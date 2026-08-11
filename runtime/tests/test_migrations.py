"""Tests for runtime.migrations schema versioning and backup."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from runtime.migrations import CURRENT_VERSION, MigrationRunner, backup_database


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """Create a minimal test database with a memories table."""
    path = tmp_path / "test.db"
    with sqlite3.connect(path) as conn:
        conn.execute("""
            CREATE TABLE memories (
                id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                content TEXT NOT NULL,
                source TEXT,
                meta TEXT,
                created_at TEXT NOT NULL,
                valid_from TEXT NOT NULL,
                valid_to TEXT
            )
        """)
        conn.commit()
    return path


class TestMigrationRunner:
    def test_fresh_db_migrates_to_current(self, db_path: Path) -> None:
        runner = MigrationRunner(db_path)
        version = runner.run_migrations()
        assert version == CURRENT_VERSION

    def test_idempotent(self, db_path: Path) -> None:
        runner = MigrationRunner(db_path)
        runner.run_migrations()
        version = runner.run_migrations()
        assert version == CURRENT_VERSION

    def test_version_tracking(self, db_path: Path) -> None:
        runner = MigrationRunner(db_path)
        runner.run_migrations()
        with sqlite3.connect(db_path) as conn:
            row = conn.execute(
                "SELECT version FROM _schema_version ORDER BY applied_at DESC LIMIT 1"
            ).fetchone()
            assert row is not None
            assert row[0] == CURRENT_VERSION

    def test_relations_table_created(self, db_path: Path) -> None:
        runner = MigrationRunner(db_path)
        runner.run_migrations()
        with sqlite3.connect(db_path) as conn:
            tables = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()]
            assert "relations" in tables

    def test_indexes_created(self, db_path: Path) -> None:
        runner = MigrationRunner(db_path)
        runner.run_migrations()
        with sqlite3.connect(db_path) as conn:
            indexes = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()]
            assert "idx_mem_kind" in indexes
            assert "idx_mem_source" in indexes


class TestBackupDatabase:
    def test_backup_creates_file(self, db_path: Path, tmp_path: Path) -> None:
        backup_dir = tmp_path / "backups"
        backup = backup_database(db_path, backup_dir)
        assert backup is not None
        assert backup.exists()
        assert backup.stat().st_size > 0

    def test_backup_nonexistent_returns_none(self, tmp_path: Path) -> None:
        backup_dir = tmp_path / "backups"
        result = backup_database(tmp_path / "nonexistent.db", backup_dir)
        assert result is None

    def test_retention_keeps_max_backups(self, db_path: Path, tmp_path: Path) -> None:
        backup_dir = tmp_path / "backups"
        for _ in range(7):
            backup_database(db_path, backup_dir, max_backups=3)
        backups = list(backup_dir.glob("test_backup_*.db"))
        assert len(backups) <= 3
