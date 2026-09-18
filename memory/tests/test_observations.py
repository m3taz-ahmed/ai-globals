"""Tests for memory.observations - capture/compress/inject loop + hook handling."""

from __future__ import annotations

from pathlib import Path

import pytest

from memory.observations import (
    KIND_FILE_EDIT,
    KIND_MCP,
    KIND_PROMPT,
    KIND_SESSION_END,
    KIND_SESSION_START,
    KIND_SHELL,
    MAX_PATHS,
    Observation,
    ObservationStore,
    _clip,
    default_db_path,
    handle_hook,
    session_id_of,
    summarize_event,
)
from runtime.schemas import StorageError, ValidationError


@pytest.fixture
def store(tmp_path: Path) -> ObservationStore:
    return ObservationStore(tmp_path / "state" / "observations.db")


# --- helpers -----------------------------------------------------------------


def test_clip_under_and_over_limit() -> None:
    assert _clip("short", 10) == "short"
    assert _clip("x" * 300, 10) == "x" * 9 + "…"
    assert _clip(123, 10) == "123"


def test_session_id_of_variants() -> None:
    assert session_id_of({"session_id": "a"}) == "a"
    assert session_id_of({"sessionId": "b"}) == "b"
    assert session_id_of({"conversation_id": "c"}) == "c"
    assert session_id_of({"conversationId": "d"}) == "d"
    assert session_id_of({"generationId": "e"}) == "e"
    assert session_id_of({"session_id": 5, "sessionId": "f"}) == "f"
    assert session_id_of({}) == "default"
    assert session_id_of({"session_id": ""}) == "default"


# --- summarize_event ----------------------------------------------------------


def test_summarize_file_edit() -> None:
    title, _d, _t, paths, kind = summarize_event("afterFileEdit", {"file_path": "src/app.py"})
    assert kind == KIND_FILE_EDIT
    assert "src/app.py" in title
    assert paths == ("src/app.py",)


def test_summarize_file_edit_no_path() -> None:
    title, _d, _t, paths, kind = summarize_event("afterFileEdit", {})
    assert kind == KIND_FILE_EDIT
    assert title == "Edited file"
    assert paths == ()


def test_summarize_shell_variants() -> None:
    title, _d, tool, _p, kind = summarize_event("afterShellExecution", {"command": "pytest -q"})
    assert kind == KIND_SHELL
    assert "pytest -q" in title
    assert tool == "pytest -q"
    title2, _d2, _t2, _p2, _k2 = summarize_event("afterShellExecution", {"cmd": "ls"})
    assert "ls" in title2
    title3, _d3, _t3, _p3, _k3 = summarize_event("afterShellExecution", {"tool_name": "Run"})
    assert "Run" in title3
    title4, *_ = summarize_event("afterShellExecution", {})
    assert "command" in title4


def test_summarize_mcp() -> None:
    title, _d, _tool, _p, kind = summarize_event("afterMCPExecution", {"tool_name": "context7"})
    assert kind == KIND_MCP
    assert "context7" in title
    t2, *_ = summarize_event("afterMCPExecution", {"method": "tools/call"})
    assert "tools/call" in t2
    t3, *_ = summarize_event("afterMCPExecution", {})
    assert "call" in t3


def test_summarize_prompt() -> None:
    title, _d, _t, _p, kind = summarize_event("beforeSubmitPrompt", {"prompt": "fix the bug"})
    assert kind == KIND_PROMPT
    assert "fix the bug" in title
    t2, *_ = summarize_event("beforeSubmitPrompt", {"text": "hello"})
    assert "hello" in t2
    t3, *_ = summarize_event("beforeSubmitPrompt", {})
    assert "Prompt:" in t3


def test_summarize_session_and_unknown_events() -> None:
    _t, _d, _to, _p, kind = summarize_event("stop", {})
    assert kind == KIND_SESSION_END
    _t2, _d2, _to2, _p2, kind2 = summarize_event("session-init", {})
    assert kind2 == KIND_SESSION_START
    title3, _d3, _to3, _p3, kind3 = summarize_event("weird-custom", {})
    assert kind3 == KIND_PROMPT
    assert "Prompt:" in title3
    title4, _d4, _to4, _p4, kind4 = summarize_event(KIND_MCP, {})
    assert kind4 == KIND_MCP
    assert "MCP" in title4


def test_summarize_empty_payload_detail() -> None:
    _t, detail, _to, _p, _k = summarize_event("stop", {})
    assert detail == ""


def test_extract_paths_nested_and_capped() -> None:
    payload = {
        "a": {"file_path": "one.py"},
        "b": [{"filePath": "two.py"}, {"file": "two.py"}, {"target_file": "three.py"}],
        "c": {"path": 42, "deep": {"deep": {"deep": {"deep": {"deep": {"filename": "x"}}}}}},
    }
    _t, _d, _to, paths, _k = summarize_event("afterFileEdit", payload)
    assert "one.py" in paths
    assert "two.py" in paths
    assert "three.py" in paths
    assert len(paths) <= MAX_PATHS


def test_extract_paths_cap() -> None:
    payload = {"files": [{"file_path": f"f{i}.py"} for i in range(MAX_PATHS + 5)]}
    _t, _d, _to, paths, _k = summarize_event("afterFileEdit", payload)
    assert len(paths) == MAX_PATHS


def test_extract_paths_cap_inside_dict_loop() -> None:
    inner = {
        k: f"{k}.py"
        for k in (
            "file_path",
            "filePath",
            "filepath",
            "path",
            "file",
            "filename",
            "target_file",
            "targetFile",
        )
    }
    payload = {"a": inner, "b": {"file_path": "x9"}, "c": {"file_path": "x10"}, "d": {"file_path": "x11"}}
    _t, _d, _to, paths, _k = summarize_event("afterFileEdit", payload)
    assert len(paths) == MAX_PATHS


# --- ObservationStore ---------------------------------------------------------


def test_init_creates_schema(store: ObservationStore) -> None:
    assert store.db_path.exists()
    assert store.count() == 0


def test_init_storage_error(tmp_path: Path) -> None:
    db_dir = tmp_path / "obsdir"
    db_dir.mkdir()
    with pytest.raises(StorageError):
        ObservationStore(db_dir)


def test_enqueue_requires_ids(store: ObservationStore) -> None:
    with pytest.raises(ValidationError):
        store.enqueue("", "event", {})
    with pytest.raises(ValidationError):
        store.enqueue("s1", "", {})


def test_enqueue_and_pending(store: ObservationStore) -> None:
    row_id = store.enqueue("s1", "afterFileEdit", {"file_path": "a.py"})
    assert row_id
    store.enqueue("s2", "stop", {})
    all_rows = store.pending()
    assert len(all_rows) == 2
    s1 = store.pending("s1")
    assert len(s1) == 1
    assert s1[0]["payload"] == {"file_path": "a.py"}
    assert s1[0]["id"] == row_id


def test_pending_corrupt_payload(store: ObservationStore) -> None:
    row_id = store.enqueue("s1", "x", {})
    with store._connect() as conn:
        conn.execute("UPDATE pending_events SET payload = ? WHERE id = ?", ("{bad", row_id))
    rows = store.pending("s1")
    assert rows[0]["payload"] == {}


def test_enqueue_storage_error(store: ObservationStore) -> None:
    with store._connect() as conn:
        conn.execute("DROP TABLE pending_events")
    with pytest.raises(StorageError):
        store.enqueue("s1", "x", {})


def test_record_validates_kind(store: ObservationStore) -> None:
    with pytest.raises(ValidationError):
        store.record("s1", "bogus", "tool", "t", "d")


def test_record_and_dedup(store: ObservationStore) -> None:
    obs = store.record("s1", KIND_SHELL, "pytest", "Ran pytest", "detail")
    assert obs is not None
    assert obs.kind == KIND_SHELL
    assert obs.to_dict()["paths"] == []
    dup = store.record("s1", KIND_SHELL, "pytest", "Ran pytest", "detail")
    assert dup is None
    other = store.record("s2", KIND_SHELL, "pytest", "Ran pytest", "detail")
    assert other is not None


def test_record_storage_error(store: ObservationStore) -> None:
    with store._connect() as conn:
        conn.execute("DROP TABLE observations")
    with pytest.raises(StorageError):
        store.record("s1", KIND_SHELL, "t", "t", "d")


def test_record_event_new_and_dup(store: ObservationStore) -> None:
    obs = store.record_event("s1", "afterFileEdit", {"file_path": "x.py"})
    assert obs is not None
    assert obs.kind == KIND_FILE_EDIT
    assert store.pending() == []
    dup = store.record_event("s1", "afterFileEdit", {"file_path": "x.py"})
    assert dup is None


def test_process_pending_drains_in_order(store: ObservationStore) -> None:
    store.enqueue("s1", "afterFileEdit", {"file_path": "a.py"})
    store.enqueue("s1", "stop", {})
    store.enqueue("s2", "stop", {})
    obs = store.process_pending("s1")
    assert len(obs) == 2
    assert store.pending("s1") == []
    assert len(store.pending("s2")) == 1


def test_process_pending_survives_failure(store: ObservationStore) -> None:
    store.enqueue("s1", "afterFileEdit", {"file_path": "a.py"})
    with store._connect() as conn:
        conn.execute("DROP TABLE observations")
    with pytest.raises(StorageError):
        store.process_pending("s1")
    assert len(store.pending("s1")) == 1
    ObservationStore(store.db_path)
    obs = store.process_pending("s1")
    assert len(obs) == 1
    assert store.pending("s1") == []


def test_recent_orders_and_filters(store: ObservationStore) -> None:
    store.record("s1", KIND_SHELL, "a", "first", "")
    store.record("s1", KIND_SHELL, "b", "second", "")
    store.record("s2", KIND_MCP, "c", "other", "")
    all_obs = store.recent()
    assert len(all_obs) == 3
    assert all_obs[0].title in {"first", "second", "other"}
    s1 = store.recent(session_id="s1")
    assert {o.title for o in s1} == {"first", "second"}
    limited = store.recent(limit=1)
    assert len(limited) == 1


def test_search_matches(store: ObservationStore) -> None:
    store.record("s1", KIND_FILE_EDIT, "t", "Edited app.py", "", ("app.py",))
    store.record("s1", KIND_SHELL, "t", "Ran pytest", "")
    hits = store.search("app.py")
    assert len(hits) == 1
    assert hits[0].title == "Edited app.py"
    assert store.search("nothing-matches") == []


def test_context_block(store: ObservationStore) -> None:
    assert store.context_block() == ""
    store.record("s1", KIND_FILE_EDIT, "t", "Edited app.py", "", ("app.py", "b.py"))
    store.record("s1", KIND_SHELL, "t", "Ran pytest", "")
    block = store.context_block(session_id="s1")
    assert "### Recent observations" in block
    assert "Edited app.py (app.py, b.py)" in block
    pytest_line = next(line for line in block.splitlines() if "Ran pytest" in line)
    assert "(" not in pytest_line


def test_context_block_with_query(store: ObservationStore) -> None:
    store.record("s1", KIND_FILE_EDIT, "t", "Edited app.py", "", ("app.py",))
    store.record("s1", KIND_SHELL, "t", "Ran pytest", "")
    block = store.context_block(query="pytest")
    assert "Ran pytest" in block
    assert "Edited" not in block


def test_session_summary(store: ObservationStore) -> None:
    empty = store.session_summary("nope")
    assert empty["observations"] == 0
    assert empty["duration_s"] == 0.0
    store.record("s1", KIND_SHELL, "t", "a", "")
    store.record("s1", KIND_FILE_EDIT, "t", "b", "")
    summary = store.session_summary("s1")
    assert summary["observations"] == 2
    assert summary["kinds"] == {KIND_SHELL: 1, KIND_FILE_EDIT: 1}


def test_default_db_path(tmp_path: Path) -> None:
    assert default_db_path(tmp_path) == tmp_path / "state" / "observations.db"


def test_observation_dataclass_fields(store: ObservationStore) -> None:
    obs = store.record("s1", KIND_MCP, "ctx7", "MCP ctx7", "d", ("p.py",))
    assert obs is not None
    assert isinstance(obs, Observation)
    row = obs.to_dict()
    assert row["session_id"] == "s1"
    assert row["paths"] == ["p.py"]


# --- handle_hook ---------------------------------------------------------------


def test_handle_hook_inject_empty(tmp_path: Path) -> None:
    assert handle_hook("inject", tmp_path, {}) == ""


def test_handle_hook_inject_with_data(tmp_path: Path) -> None:
    handle_hook("observe", tmp_path, {"session_id": "s1", "file_path": "a.py"}, kind="file_edit")
    block = handle_hook("inject", tmp_path, {"session_id": "s1"})
    assert "### Recent observations" in block


def test_handle_hook_inject_with_query(tmp_path: Path) -> None:
    handle_hook("observe", tmp_path, {"command": "pytest"}, kind="shell")
    hit = handle_hook("inject", tmp_path, {"prompt": "pytest"})
    assert "pytest" in hit
    miss = handle_hook("inject", tmp_path, {"prompt": "nomatch"})
    assert miss == ""
    numeric = handle_hook("inject", tmp_path, {"prompt": 42})
    assert isinstance(numeric, str)


def test_handle_hook_observe(tmp_path: Path) -> None:
    out = handle_hook("observe", tmp_path, {"session_id": "s1", "file_path": "x.py"}, kind="file_edit")
    assert out == ""
    store = ObservationStore(default_db_path(tmp_path))
    assert store.count() == 1


def test_handle_hook_observe_defaults(tmp_path: Path) -> None:
    handle_hook("observe", tmp_path, {}, event="stop")
    store = ObservationStore(default_db_path(tmp_path))
    assert store.count() == 1


def test_handle_hook_summary(tmp_path: Path) -> None:
    assert handle_hook("summary", tmp_path, {"session_id": "empty"}) == ""
    handle_hook("observe", tmp_path, {"session_id": "s1", "file_path": "x.py"}, kind="file_edit")
    handle_hook("observe", tmp_path, {"session_id": "s1", "command": "ls"}, kind="shell")
    out = handle_hook("summary", tmp_path, {"session_id": "s1"})
    assert "Session summary: 2 observations" in out
    assert "file_edit:1" in out
    assert "shell:1" in out


def test_handle_hook_unknown_action(tmp_path: Path) -> None:
    assert handle_hook("bogus", tmp_path, {}) == ""


def test_handle_hook_never_raises(tmp_path: Path) -> None:
    bad_root = tmp_path / "afile"
    bad_root.write_text("x")
    assert handle_hook("inject", bad_root, {}) == ""
    assert handle_hook("observe", bad_root, {}) == ""
    assert handle_hook("summary", bad_root, {}) == ""
