"""Gap-coverage tests for runtime/migrations.py.

Covers: compute_schema_hash, peek_version, rollback paths, hash-mismatch
fail-closed, and backup retention edge cases.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from runtime import migrations
from runtime.migrations import (
    CURRENT_VERSION,
    MigrationRunner,
    backup_database,
    compute_schema_hash,
    register_hash_edge,
)


@pytest.fixture()
def db_path(tmp_path):
    return tmp_path / "test.db"


def _make_base_db(path: Path) -> None:
    """Create the memories table the built-in migrations index."""
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE memories (id TEXT, kind TEXT, source TEXT, valid_to TEXT)")


class TestComputeSchemaHash:
    def test_deterministic(self, db_path):
        _make_base_db(db_path)
        with sqlite3.connect(db_path) as conn:
            h1 = compute_schema_hash(conn)
            h2 = compute_schema_hash(conn)
        assert h1 == h2 and len(h1) == 64

    def test_changes_with_schema(self, db_path):
        _make_base_db(db_path)
        with sqlite3.connect(db_path) as conn:
            h1 = compute_schema_hash(conn)
            conn.execute("CREATE TABLE extra (id TEXT)")
            h2 = compute_schema_hash(conn)
        assert h1 != h2

    def test_index_included(self, db_path):
        _make_base_db(db_path)
        with sqlite3.connect(db_path) as conn:
            h1 = compute_schema_hash(conn)
            conn.execute("CREATE INDEX idx_x ON memories(kind)")
            h2 = compute_schema_hash(conn)
        assert h1 != h2


class TestPeekVersion:
    def test_missing_db_returns_zero(self, tmp_path):
        assert MigrationRunner(tmp_path / "nope.db").peek_version() == 0

    def test_unversioned_db_returns_zero(self, db_path):
        _make_base_db(db_path)
        assert MigrationRunner(db_path).peek_version() == 0

    def test_peek_after_migrate(self, db_path):
        _make_base_db(db_path)
        r = MigrationRunner(db_path)
        r.run_migrations()
        assert r.peek_version() == CURRENT_VERSION

    def test_peek_is_readonly(self, db_path):
        _make_base_db(db_path)
        r = MigrationRunner(db_path)
        r.peek_version()
        # DB unchanged — no _schema_version table created by a read-only peek
        with sqlite3.connect(db_path) as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE name='_schema_version'"
            ).fetchall()
        assert rows == []


class TestRollback:
    def test_rollback_to_zero(self, db_path):
        _make_base_db(db_path)
        r = MigrationRunner(db_path)
        r.run_migrations()
        assert r.rollback(0) == 0
        with sqlite3.connect(db_path) as conn:
            tables = {row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
        assert "relations" not in tables

    def test_rollback_stepwise(self, db_path):
        _make_base_db(db_path)
        r = MigrationRunner(db_path)
        r.run_migrations()
        assert r.rollback(1) == 1
        with sqlite3.connect(db_path) as conn:
            tables = {row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
        assert "relations" not in tables

    def test_rollback_already_below(self, db_path):
        _make_base_db(db_path)
        r = MigrationRunner(db_path)
        r.run_migrations()
        assert r.rollback(0) == 0
        assert r.rollback(0) == 0  # second call is a no-op

    def test_rollback_future_raises(self, db_path):
        r = MigrationRunner(db_path)
        with pytest.raises(NotImplementedError):
            r.rollback(CURRENT_VERSION + 5)

    def test_rollback_unregistered_raises(self, db_path, monkeypatch):
        _make_base_db(db_path)
        r = MigrationRunner(db_path)
        r.run_migrations()
        saved = migrations._ROLLBACK_MIGRATIONS.pop(0)
        try:
            with pytest.raises(ValueError, match="No rollback registered"):
                r.rollback(0)
        finally:
            migrations._ROLLBACK_MIGRATIONS[0] = saved


class TestHashVerification:
    def test_matching_hash_passes(self, db_path, tmp_path):
        _make_base_db(db_path)
        # Learn the real post-migration schema hash from a scratch DB that ran
        # the actual migration (includes the _schema_version bookkeeping table).
        scratch = tmp_path / "scratch.db"
        _make_base_db(scratch)
        migrations._MIGRATIONS[0](conn := sqlite3.connect(scratch))
        conn.execute(
            "CREATE TABLE IF NOT EXISTS _schema_version (version INTEGER, applied_at TEXT)")
        real_hash = compute_schema_hash(conn)
        conn.close()
        register_hash_edge(0, 1, real_hash)
        try:
            assert MigrationRunner(db_path).run_migrations() == CURRENT_VERSION
        finally:
            register_hash_edge(0, 1, "")

    def test_mismatch_raises(self, db_path):
        _make_base_db(db_path)
        register_hash_edge(0, 1, "0" * 64)
        try:
            with pytest.raises(RuntimeError, match="hash mismatch"):
                MigrationRunner(db_path).run_migrations()
        finally:
            register_hash_edge(0, 1, "")


class TestBackupEdgeCases:
    def test_keep_none_deletes_all(self, tmp_path):
        db = tmp_path / "x.db"
        db.write_bytes(b"data")
        bdir = tmp_path / "bk"
        result = backup_database(db, bdir, max_backups=0)
        # backup created then immediately removed by retention
        assert result is not None
        assert list(bdir.glob("*.db")) == []

    def test_timestamp_collision_counter(self, tmp_path):
        db = tmp_path / "x.db"
        db.write_bytes(b"data")
        bdir = tmp_path / "bk"
        b1 = backup_database(db, bdir)
        b2 = backup_database(db, bdir)
        assert b1 is not None and b2 is not None and b1 != b2
