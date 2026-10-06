"""Gap tests for memory/checkpoint.py."""
from __future__ import annotations

import json
import sqlite3

import pytest

from memory.checkpoint import (
    Checkpoint,
    SqliteCheckpointSaver,
    create_checkpoint,
)


class TestFromDict:
    def test_non_dict_raises(self):
        with pytest.raises(ValueError, match="mapping"):
            Checkpoint.from_dict("notadict")  # type: ignore[arg-type]

    def test_bad_section_raises(self):
        with pytest.raises(ValueError, match="mappings"):
            Checkpoint.from_dict({
                "checkpoint_id": "c", "created_at": 1.0,
                "channel_values": "notadict", "channel_versions": {},
                "metadata": {},
            })


class TestCreateCheckpoint:
    def test_root_honors_versions(self):
        cp = create_checkpoint(channel_values={"a": 1}, channel_versions={"z": 9})
        assert cp.channel_versions["a"] == 1
        assert cp.channel_versions["z"] == 9

    def test_child_ignores_supplied_versions(self):
        parent = create_checkpoint(channel_values={"a": 1})
        child = create_checkpoint(parent=parent, channel_values={"a": 2},
                                  channel_versions={"a": 99})
        assert child.channel_versions["a"] == 2  # computed, not 99


class TestSaver:
    def _saver(self, tmp_path):
        return SqliteCheckpointSaver(tmp_path / "cp.db")

    def test_closed_raises(self, tmp_path):
        s = self._saver(tmp_path)
        s.close()
        with pytest.raises(ValueError, match="closed"):
            s.get({"thread_id": "t"})
        s.close()  # idempotent

    def test_missing_thread_id_raises(self, tmp_path):
        s = self._saver(tmp_path)
        with pytest.raises(ValueError, match="thread_id"):
            s._config_thread({})

    def test_bad_limit_defaults(self, tmp_path):
        s = self._saver(tmp_path)
        cp = create_checkpoint(channel_values={"x": 1})
        s.put({"thread_id": "t"}, cp, {})
        out = s.list({"thread_id": "t"}, limit="bad")  # type: ignore[arg-type]
        assert len(out) == 1

    def test_specific_checkpoint_get(self, tmp_path):
        s = self._saver(tmp_path)
        cp = create_checkpoint(channel_values={"x": 1})
        s.put({"thread_id": "t"}, cp, {"m": 1})
        got = s.get({"thread_id": "t", "checkpoint_id": cp.checkpoint_id})
        assert got is not None
        assert got.channel_values == {"x": 1}
        assert got.metadata["m"] == 1
        assert got.metadata["thread_id"] == "t"

    def test_corrupt_row_raises(self, tmp_path):
        s = self._saver(tmp_path)
        cp = create_checkpoint()
        s.put({"thread_id": "t"}, cp, {})
        # corrupt the stored JSON directly
        s._conn.execute(
            "UPDATE checkpoints SET channel_values='{bad' WHERE id=?",
            (cp.checkpoint_id,))
        s._conn.commit()
        with pytest.raises(ValueError, match="Corrupt"):
            s.get({"thread_id": "t"})

    def test_thread_id_backfill_migration(self, tmp_path):
        db = tmp_path / "old.db"
        # simulate a pre-thread_id DB
        with sqlite3.connect(db) as conn:
            conn.execute("""CREATE TABLE checkpoints (
                id TEXT PRIMARY KEY, parent_id TEXT, created_at REAL,
                channel_values TEXT, channel_versions TEXT, metadata TEXT)""")
            conn.execute(
                "INSERT INTO checkpoints VALUES (?,?,?,?,?,?)",
                ("c1", None, 1.0, "{}", "{}", json.dumps({"thread_id": "legacy"})),
            )
        s = SqliteCheckpointSaver(db)
        row = s._conn.execute("SELECT thread_id FROM checkpoints WHERE id='c1'").fetchone()
        assert row[0] == "legacy"
        s.close()
