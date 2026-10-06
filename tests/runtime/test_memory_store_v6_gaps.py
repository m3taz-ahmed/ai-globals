"""Coverage-gap tests for memory/store.py v6 paths (hooks, vectors, keys, arcs)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from memory.store import Memory, MemoryStore
from runtime.hook_lifecycle import HookPhase, HookRegistry


def _store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(root=tmp_path, enable_vector=False)


class _FakeVector:
    def __init__(self) -> None:
        self.added: list[tuple[str, str]] = []
        self.batched: list[str] = []
        self.removed: list[str] = []

    def is_available(self) -> bool:
        return True

    def add(self, mem_id: str, content: str) -> None:
        self.added.append((mem_id, content))

    def add_batch(self, ids: list[str], contents: list[str]) -> None:
        self.batched.extend(ids)

    def remove(self, mem_id: str) -> None:
        self.removed.append(mem_id)


def test_as_of_with_kind(tmp_path: Path) -> None:
    s = _store(tmp_path)
    s.add("fact", "some fact")
    s.add("note", "some note")
    only_facts = s.as_of(kind="fact")
    assert all(m.kind == "fact" for m in only_facts)


def test_list_all_kind_filter(tmp_path: Path) -> None:
    s = _store(tmp_path)
    s.add("fact", "f1")
    s.add("note", "n1")
    got = s.list_all(kind="fact")
    assert len(got) == 1 and got[0].kind == "fact"


def test_integrity_key_files_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    empty = tmp_path / "ext.key"
    empty.write_text("", encoding="utf-8")
    monkeypatch.setenv("AIZEE_INTEGRITY_KEY_FILE", str(empty))
    monkeypatch.delenv("AIZEE_INTEGRITY_KEY", raising=False)
    MemoryStore(root=tmp_path / "root", enable_vector=False)
    # external file empty -> fell through to state/integrity.key
    assert (tmp_path / "root" / "state" / "integrity.key").exists()


def test_integrity_key_file_present(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    real = tmp_path / "ext.key"
    real.write_text("deadbeef" * 8, encoding="utf-8")
    monkeypatch.setenv("AIZEE_INTEGRITY_KEY_FILE", str(real))
    s = MemoryStore(root=tmp_path / "r2", enable_vector=False)
    m = s.add("fact", "x")
    assert m.integrity == "ok"


def test_decay_table_missing_recovers(tmp_path: Path) -> None:
    s = _store(tmp_path)
    m = s.add("fact", "x")
    with s._conn() as conn:
        conn.execute("DROP TABLE memory_decay")
    s.record_access(m.id)  # _migrate_decay_table early-returns when table is absent
    assert s.get_decay_score(m.id) >= 0.0


def _veto_registry() -> HookRegistry:
    reg = HookRegistry()

    @reg.on(HookPhase.MEMORY_PRE_WRITE)
    def _veto(ctx) -> None:
        ctx.stop()

    return reg


def test_hook_veto_blocks_add(tmp_path: Path) -> None:
    s = _store(tmp_path)
    s.set_hooks(_veto_registry())
    from runtime.hook_lifecycle import HookError

    with pytest.raises(HookError):
        s.add("fact", "vetoed")


def test_hook_veto_filters_batch(tmp_path: Path) -> None:
    s = _store(tmp_path)
    reg = HookRegistry()

    @reg.on(HookPhase.MEMORY_PRE_WRITE)
    def _drop_bad(ctx) -> None:
        if "bad" in ctx.attributes.get("content", ""):
            ctx.stop()

    s.set_hooks(reg)
    mem = Memory(
        id="m_ok", kind="fact", content="good content", source="", meta="{}",
        created_at="2020-01-01T00:00:00+00:00", valid_from="2020-01-01T00:00:00+00:00",
        valid_to=None,
    )
    bad = Memory(
        id="m_bad", kind="fact", content="bad content", source="", meta="{}",
        created_at="2020-01-01T00:00:00+00:00", valid_from="2020-01-01T00:00:00+00:00",
        valid_to=None,
    )
    persisted = s.add_batch([mem, bad])
    assert [m.id for m in persisted] == ["m_ok"]


def test_add_with_identity_scoping(tmp_path: Path) -> None:
    s = _store(tmp_path)
    m = s.add(
        "fact", "scoped", user_id="u1", agent_id="a1", session_id="s1",
    )
    meta = json.loads(m.meta)
    assert meta["user_id"] == "u1" and meta["agent_id"] == "a1" and meta["session_id"] == "s1"


def test_add_batch_all_preexisting_skips_vector(tmp_path: Path) -> None:
    s = _store(tmp_path)
    mem = s.add("fact", "already there")
    fv = _FakeVector()
    s.vector = fv  # type: ignore[assignment]
    # Re-add identical Memory objects -> all pre-existing -> vector skipped.
    out = s.add_batch([mem])
    assert fv.batched == [] and out == [mem]


def test_soft_delete_removes_vector(tmp_path: Path) -> None:
    s = _store(tmp_path)
    m = s.add("fact", "to delete")
    fv = _FakeVector()
    s.vector = fv  # type: ignore[assignment]
    assert s.soft_delete(m.id)
    assert fv.removed == [m.id]


def test_restore_reindexes_vector(tmp_path: Path) -> None:
    s = _store(tmp_path)
    m = s.add("fact", "to restore")
    fv = _FakeVector()
    s.vector = fv  # type: ignore[assignment]
    s.soft_delete(m.id)
    assert s.restore(m.id)
    assert fv.added == [(m.id, m.content)]


def test_restore_nonexistent_returns_false(tmp_path: Path) -> None:
    s = _store(tmp_path)
    assert s.restore("mem_missing") is False


def test_detect_contradictions_skips_bad_meta(tmp_path: Path) -> None:
    s = _store(tmp_path)
    good = s.add("fact", "a", meta={"subject": "x"})
    s.add("fact", "b", meta={"subject": "x"})
    s.add("fact", "c", meta={"other": 1})  # no subject -> skipped
    with s._conn() as conn:
        conn.execute(
            "INSERT INTO memories (id, kind, content, source, meta, created_at, valid_from)"
            " VALUES ('badmeta', 'fact', 'z', '', 'not json{', '2020', '2020')"
        )
    groups = s.detect_contradictions()
    assert {good.id} <= set(groups[0]) and "badmeta" not in set(groups[0])


def test_resolve_empty_set_returns_none(tmp_path: Path) -> None:
    s = _store(tmp_path)
    assert s.resolve_contradictions(["does-not-exist"]) is None


def test_merge_skips_self_soft_delete(tmp_path: Path) -> None:
    s = _store(tmp_path)
    # Inputs whose merged content equals input1's content AND same source ->
    # merged id == input1 id -> the self-protect arc fires.
    a = s.add("fact", "A\nB", source="contradiction-merge", meta={"subject": "x"})
    b = s.add("fact", "A", source="contradiction-merge", meta={"subject": "x"})
    winner = s.resolve_contradictions([a.id, b.id], strategy="merge")
    assert winner is not None and winner.id == a.id
    kept = s.get(a.id)
    assert kept is not None and kept.deleted_at is None


def test_confidence_bad_meta_defaults(tmp_path: Path) -> None:
    s = _store(tmp_path)
    good = Memory(
        id="c1", kind="fact", content="x", source="", meta='{"confidence": 0.9}',
        created_at="2020-01-01T00:00:00+00:00", valid_from="2020-01-01T00:00:00+00:00",
        valid_to=None,
    )
    bad = Memory(
        id="c2", kind="fact", content="y", source="", meta="not json{",
        created_at="2020-01-02T00:00:00+00:00", valid_from="2020-01-02T00:00:00+00:00",
        valid_to=None,
    )
    winner = s._pick_winner([bad, good], "confidence", [])
    assert winner.id == "c1"


def test_migrate_decay_table_absent(tmp_path: Path) -> None:
    s = _store(tmp_path)
    with s._conn() as conn:
        conn.execute("DROP TABLE memory_decay")
    s._migrate_decay_table()  # row is None -> early return, no crash


def test_integrity_key_file_missing_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AIZEE_INTEGRITY_KEY_FILE", str(tmp_path / "no-such.key"))
    monkeypatch.delenv("AIZEE_INTEGRITY_KEY", raising=False)
    s = MemoryStore(root=tmp_path / "r3", enable_vector=False)
    assert s.add("fact", "x").integrity == "ok"


def test_integrity_state_key_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AIZEE_INTEGRITY_KEY", raising=False)
    monkeypatch.delenv("AIZEE_INTEGRITY_KEY_FILE", raising=False)
    root = tmp_path / "r4"
    (root / "state").mkdir(parents=True)
    (root / "state" / "integrity.key").write_text("", encoding="utf-8")
    MemoryStore(root=root, enable_vector=False)
    # Empty on-disk key -> regenerated in place.
    assert (root / "state" / "integrity.key").read_text().strip() != ""


def test_vetoed_by_hooks_none_when_unset(tmp_path: Path) -> None:
    s = _store(tmp_path)
    m = s.add("fact", "x")
    assert s._vetoed_by_hooks(m) is False


def test_pick_winner_empty_mem_ids(tmp_path: Path) -> None:
    s = _store(tmp_path)
    assert s._rowids_for([]) == {}
