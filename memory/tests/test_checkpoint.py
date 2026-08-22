"""Tests for memory/checkpoint.py — checkpoint-based durable state."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from memory.checkpoint import (
    AizeeAgentState,
    BaseCheckpointSaver,
    Checkpoint,
    SqliteCheckpointSaver,
    append_reducer,
    create_checkpoint,
    last_value_reducer,
    subtract_reducer,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def saver(tmp_path: Path) -> SqliteCheckpointSaver:
    return SqliteCheckpointSaver(tmp_path / "checkpoints.db")


@pytest.fixture
def config() -> dict[str, str]:
    return {"thread_id": "thread-1"}


# ---------------------------------------------------------------------------
# Channel reducers
# ---------------------------------------------------------------------------

class TestReducers:
    def test_append_reducer_concatenates(self):
        assert append_reducer(["a"], ["b", "c"]) == ["a", "b", "c"]

    def test_append_reducer_handles_none(self):
        assert append_reducer(None, ["b"]) == ["b"]
        assert append_reducer(["a"], None) == ["a"]
        assert append_reducer(None, None) == []

    def test_last_value_reducer_replaces(self):
        assert last_value_reducer("old", "new") == "new"
        assert last_value_reducer(None, "new") == "new"

    def test_subtract_reducer_decrements(self):
        assert subtract_reducer(10.0, 3.0) == 7.0

    def test_subtract_reducer_handles_none(self):
        assert subtract_reducer(None, 5.0) == -5.0


# ---------------------------------------------------------------------------
# Checkpoint data model
# ---------------------------------------------------------------------------

class TestCheckpointModel:
    def test_checkpoint_creation_defaults(self):
        cp = Checkpoint(
            checkpoint_id="cp-1",
            parent_id=None,
            created_at=1000.0,
            channel_values={"messages": ["hi"]},
            channel_versions={"messages": 1},
        )
        assert cp.metadata == {}
        assert cp.parent_id is None

    def test_checkpoint_to_dict_roundtrip(self):
        cp = Checkpoint(
            checkpoint_id="cp-1",
            parent_id="cp-0",
            created_at=1000.0,
            channel_values={"x": 1},
            channel_versions={"x": 2},
            metadata={"step": 1},
        )
        data = cp.to_dict()
        assert data["checkpoint_id"] == "cp-1"
        restored = Checkpoint.from_dict(data)
        assert restored == cp

    def test_create_checkpoint_bumps_versions(self):
        parent = Checkpoint(
            checkpoint_id="p",
            parent_id=None,
            created_at=1.0,
            channel_values={"messages": ["a"]},
            channel_versions={"messages": 1},
        )
        child = create_checkpoint(parent=parent, channel_values={"messages": ["b"], "persona": "x"})
        assert child.parent_id == "p"
        assert child.channel_versions["messages"] == 2
        assert child.channel_versions["persona"] == 1

    def test_create_checkpoint_root(self):
        cp = create_checkpoint(channel_values={"messages": ["hi"]})
        assert cp.parent_id is None
        assert cp.channel_versions["messages"] == 1
        assert cp.checkpoint_id  # UUID generated


# ---------------------------------------------------------------------------
# SqliteCheckpointSaver
# ---------------------------------------------------------------------------

class TestSqliteCheckpointSaver:
    def test_put_and_get_latest(self, saver, config):
        cp = create_checkpoint(channel_values={"messages": ["hello"]})
        saver.put(config, cp, {"step": 0})
        fetched = saver.get(config)
        assert fetched is not None
        assert fetched.checkpoint_id == cp.checkpoint_id
        assert fetched.channel_values["messages"] == ["hello"]

    def test_get_returns_none_when_empty(self, saver, config):
        assert saver.get(config) is None

    def test_get_specific_checkpoint_id(self, saver, config):
        cp1 = create_checkpoint(channel_values={"n": 1})
        cp2 = create_checkpoint(parent=cp1, channel_values={"n": 2})
        saver.put(config, cp1, {"step": 0})
        saver.put(config, cp2, {"step": 1})
        fetched = saver.get({**config, "checkpoint_id": cp1.checkpoint_id})
        assert fetched is not None
        assert fetched.checkpoint_id == cp1.checkpoint_id

    def test_list_returns_history_newest_first(self, saver, config):
        cp1 = create_checkpoint(channel_values={"n": 1}, metadata={"step": 0})
        cp2 = create_checkpoint(parent=cp1, channel_values={"n": 2}, metadata={"step": 1})
        cp3 = create_checkpoint(parent=cp2, channel_values={"n": 3}, metadata={"step": 2})
        for cp, meta in [(cp1, {"step": 0}), (cp2, {"step": 1}), (cp3, {"step": 2})]:
            saver.put(config, cp, meta)
        history = saver.list(config, limit=10)
        assert len(history) == 3
        assert history[0].checkpoint_id == cp3.checkpoint_id
        assert history[2].checkpoint_id == cp1.checkpoint_id

    def test_list_respects_limit(self, saver, config):
        for i in range(5):
            cp = create_checkpoint(channel_values={"i": i})
            saver.put(config, cp, {"step": i})
        history = saver.list(config, limit=2)
        assert len(history) == 2

    def test_put_requires_thread_id(self, saver):
        cp = create_checkpoint(channel_values={"x": 1})
        with pytest.raises(ValueError, match="thread_id"):
            saver.put({}, cp, {})

    def test_isolates_threads(self, saver):
        cfg_a = {"thread_id": "a"}
        cfg_b = {"thread_id": "b"}
        saver.put(cfg_a, create_checkpoint(channel_values={"t": "a"}), {})
        saver.put(cfg_b, create_checkpoint(channel_values={"t": "b"}), {})
        assert saver.get(cfg_a).channel_values["t"] == "a"
        assert saver.get(cfg_b).channel_values["t"] == "b"
        assert len(saver.list(cfg_a)) == 1
        assert len(saver.list(cfg_b)) == 1

    def test_parent_child_chain_persisted(self, saver, config):
        root = create_checkpoint(channel_values={"messages": ["root"]})
        child = create_checkpoint(parent=root, channel_values={"messages": ["child"]})
        grandchild = create_checkpoint(parent=child, channel_values={"messages": ["gc"]})
        for cp in (root, child, grandchild):
            saver.put(config, cp, {})
        history = saver.list(config, limit=10)
        ids = {cp.checkpoint_id for cp in history}
        assert {root.checkpoint_id, child.checkpoint_id, grandchild.checkpoint_id} == ids
        gc = next(cp for cp in history if cp.checkpoint_id == grandchild.checkpoint_id)
        assert gc.parent_id == child.checkpoint_id

    def test_metadata_merged_on_put(self, saver, config):
        cp = create_checkpoint(channel_values={"x": 1}, metadata={"src": "agent"})
        saver.put(config, cp, {"step": 5})
        fetched = saver.get(config)
        assert fetched is not None
        assert fetched.metadata["src"] == "agent"
        assert fetched.metadata["step"] == 5
        assert fetched.metadata["thread_id"] == "thread-1"

    def test_table_schema_created(self, tmp_path: Path):
        db = tmp_path / "cp.db"
        SqliteCheckpointSaver(db)
        with sqlite3.connect(db) as conn:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='checkpoints'"
            ).fetchone()
            assert row is not None
            cols = {r[1] for r in conn.execute("PRAGMA table_info(checkpoints)")}
            assert cols == {"id", "parent_id", "created_at", "channel_values", "channel_versions", "metadata"}


# ---------------------------------------------------------------------------
# AizeeAgentState TypedDict
# ---------------------------------------------------------------------------

class TestAizeeAgentState:
    def test_state_is_typeddict(self):
        # TypedDicts are plain dicts at runtime; verify field presence.
        state: AizeeAgentState = {
            "messages": ["hi"],
            "current_persona": "architect",
            "budget_remaining": 100.0,
            "audit_log": [],
            "policy_decisions": [],
        }
        assert state["messages"] == ["hi"]
        assert state["current_persona"] == "architect"
        assert state["budget_remaining"] == 100.0

    def test_state_serializable_to_json(self):
        state: AizeeAgentState = {
            "messages": ["hi"],
            "current_persona": "architect",
            "budget_remaining": 100.0,
            "audit_log": ["event"],
            "policy_decisions": ["decide"],
        }
        encoded = json.dumps(state)
        assert json.loads(encoded)["messages"] == ["hi"]


# ---------------------------------------------------------------------------
# BaseCheckpointSaver ABC
# ---------------------------------------------------------------------------

class TestBaseCheckpointSaver:
    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            BaseCheckpointSaver()  # type: ignore[abstract]
