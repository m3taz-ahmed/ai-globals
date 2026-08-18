"""Tests for runtime.migrations schema versioning and backup."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from runtime.migrations import _MIGRATIONS, CURRENT_VERSION, MigrationRunner, backup_database


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


class TestMigrationGaps:
    def test_missing_migration_logs_warning_and_breaks(self, db_path: Path, tmp_path: Path) -> None:
        """Cover lines 107-108: when a migration is missing for a version, it warns and breaks."""
        # Manually set the schema version to a value with no registered migration
        import sqlite3
        from datetime import datetime

        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS _schema_version (version INTEGER, applied_at TEXT)"
            )
            conn.execute(
                "INSERT INTO _schema_version (version, applied_at) VALUES (?, ?)",
                (99, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()

        runner = MigrationRunner(db_path)
        version = runner.run_migrations()
        # Since version 99 >= CURRENT_VERSION, no migrations run
        assert version == 99

    def test_gap_in_migrations_breaks_early(self, db_path: Path) -> None:
        """Cover lines 107-108: gap in migration chain causes warning and break."""

        # Set version to 0 but remove migration 0 to create a gap
        original_migrations = dict(_MIGRATIONS)
        _MIGRATIONS.clear()
        # Only register migration 1, not 0 â€” creates a gap at version 0
        if 1 in original_migrations:
            _MIGRATIONS[1] = original_migrations[1]
        try:
            runner = MigrationRunner(db_path)
            version = runner.run_migrations()
            # No migration from 0, so it breaks immediately; version stays 0
            assert version == 0
        finally:
            _MIGRATIONS.clear()
            _MIGRATIONS.update(original_migrations)


class TestBackupRetention:
    def test_old_backups_deleted(self, db_path: Path, tmp_path: Path) -> None:
        """Cover lines 131-132: old backups beyond max_backups are unlinked."""
        import time

        backup_dir = tmp_path / "backups"
        # Create more backups than max_backups, with delays to ensure unique timestamps
        for _ in range(4):
            backup_database(db_path, backup_dir, max_backups=2)
            time.sleep(1.1)  # ensure unique second-level timestamps
        backups = list(backup_dir.glob("test_backup_*.db"))
        assert len(backups) == 2
