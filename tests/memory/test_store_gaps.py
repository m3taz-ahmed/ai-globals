"""Gap tests for memory/store.py."""
from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock

from memory.store import MemoryStore


def _store(tmp_path, **kw) -> MemoryStore:
    return MemoryStore(tmp_path, tmp_path / "memory.db", enable_vector=False, **kw)


class TestFtsSanitize:
    def test_token_stripped_to_empty(self, tmp_path):
        s = _store(tmp_path)
        # every token is only operators/punct -> sanitized out -> ""
        out = s._search._fts_query("AND OR NOT ***")
        assert out == ""

    def test_long_token_truncated(self, tmp_path):
        s = _store(tmp_path)
        out = s._search._fts_query("x" * 500)
        assert "x" * s._search._MAX_FTS_TOKEN_LEN in out


class TestIntegrityKey:
    def test_env_key_wins(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AIZEE_INTEGRITY_KEY", "envkey123")
        s = _store(tmp_path)
        assert s._integrity_key == "envkey123"

    def test_ext_key_file(self, tmp_path, monkeypatch):
        monkeypatch.delenv("AIZEE_INTEGRITY_KEY", raising=False)
        kf = tmp_path / "ext.key"
        kf.write_text("external-key\n", encoding="utf-8")
        monkeypatch.setenv("AIZEE_INTEGRITY_KEY_FILE", str(kf))
        s = _store(tmp_path)
        assert s._integrity_key == "external-key"

    def test_ext_key_file_empty_falls_through(self, tmp_path, monkeypatch):
        monkeypatch.delenv("AIZEE_INTEGRITY_KEY", raising=False)
        kf = tmp_path / "empty.key"
        kf.write_text("", encoding="utf-8")
        monkeypatch.setenv("AIZEE_INTEGRITY_KEY_FILE", str(kf))
        s = _store(tmp_path)
        # empty external -> dev fallback generated under state/
        assert s._integrity_key

    def test_existing_state_key_reused(self, tmp_path, monkeypatch):
        monkeypatch.delenv("AIZEE_INTEGRITY_KEY", raising=False)
        monkeypatch.delenv("AIZEE_INTEGRITY_KEY_FILE", raising=False)
        s1 = _store(tmp_path)
        s2 = _store(tmp_path)
        assert s1._integrity_key == s2._integrity_key


class TestRowToMemory:
    def test_missing_sig_column(self, tmp_path):
        s = _store(tmp_path)
        mid = s.add("note", "content here").id
        # query without integrity_sig column -> IndexError -> sig None
        with s._conn() as conn:
            row = conn.execute(
                "SELECT id, kind, content, source, meta, created_at, valid_from, valid_to "
                "FROM memories WHERE id=?", (mid,)).fetchone()
        mem = s._relations.row_to_memory(row)
        assert mem.integrity == "unsigned"

    def test_tampered_signature(self, tmp_path):
        s = _store(tmp_path)
        mid = s.add("note", "content").id
        with s._conn() as conn:
            conn.execute("UPDATE memories SET integrity_sig='forged' WHERE id=?", (mid,))
        with s._conn() as conn:
            row = conn.execute("SELECT * FROM memories WHERE id=?", (mid,)).fetchone()
        mem = s._relations.row_to_memory(row)
        assert mem.integrity == "tampered"


class TestDecayMigration:
    def test_no_decay_table_returns(self, tmp_path):
        db = tmp_path / "empty.db"
        sqlite3.connect(db).close()
        s = _store(tmp_path)
        s.db_path = db
        s._migrate_decay_table()  # must not raise

    def test_legacy_decay_table_migrated(self, tmp_path):
        db = tmp_path / "m.db"
        with sqlite3.connect(db) as conn:
            conn.execute("CREATE TABLE memories (id TEXT PRIMARY KEY, kind TEXT, content TEXT, source TEXT, meta TEXT, created_at REAL, valid_from REAL, valid_to REAL, integrity_sig TEXT)")
            conn.execute("INSERT INTO memories (id, kind, content, source, meta, created_at, valid_from, valid_to, integrity_sig) VALUES ('m1','n','c','','',1,1,NULL,NULL)")
            conn.execute("CREATE TABLE memory_decay (mem_id TEXT, decay_score REAL, last_accessed REAL, access_count INTEGER)")
            conn.execute("INSERT INTO memory_decay VALUES ('m1', 0.5, 1.0, 3)")
        s = _store(tmp_path)
        s.db_path = db
        def _conn():
            c = sqlite3.connect(db)
            c.row_factory = sqlite3.Row
            return c
        s._conn = _conn  # type: ignore[assignment]
        s._migrate_decay_table()
        with sqlite3.connect(db) as conn:
            ddl = conn.execute("SELECT sql FROM sqlite_master WHERE name='memory_decay'").fetchone()[0]
        assert "CASCADE" in ddl.upper()

    def test_already_cascade_returns(self, tmp_path):
        s = _store(tmp_path)  # fresh DB already has CASCADE schema
        s._migrate_decay_table()  # early return, no-op


class TestDeleteHard:
    def test_deletes_and_vector_remove(self, tmp_path):
        s = _store(tmp_path)
        mid = s.add("note", "to delete").id
        s.vector = MagicMock()
        s.vector.is_available.return_value = True
        assert s.delete_hard(mid) is True
        s.vector.remove.assert_called_once_with(mid)
        assert s.delete_hard("nonexistent") is False


class TestSchemaVerify:
    def test_drift_warns_no_raise(self, tmp_path):
        s = _store(tmp_path)
        with s._conn() as conn:
            conn.execute("CREATE TABLE stray_drift (x)")
        s._verify_schema()  # warns, never raises
