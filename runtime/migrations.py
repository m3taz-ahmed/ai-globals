#!/usr/bin/env python3
"""Schema versioning and migration framework for aiZee.

Tracks schema versions in a `_schema_version` table and provides
a migration registry for applying incremental schema changes.

Usage::

    from runtime.migrations import MigrationRunner

    runner = MigrationRunner(db_path)
    runner.run_migrations()
"""

from __future__ import annotations

import logging
import shutil
import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Current schema version
CURRENT_VERSION = 2

# Migration functions keyed by (from_version, to_version)
MigrationFn = Callable[[sqlite3.Connection], None]
_MIGRATIONS: dict[int, MigrationFn] = {}

# Rollback functions keyed by version (reverses migration to that version).
_RollbackFn = Callable[[sqlite3.Connection], None]
_ROLLBACK_MIGRATIONS: dict[int, _RollbackFn] = {}


def migration(from_version: int) -> Callable[[MigrationFn], MigrationFn]:
    """Decorator to register a migration from a given version to from_version+1."""

    def decorator(fn: MigrationFn) -> MigrationFn:
        _MIGRATIONS[from_version] = fn
        return fn

    return decorator


def rollback(to_version: int) -> Callable[[_RollbackFn], _RollbackFn]:
    """Decorator to register a rollback from to_version+1 back to to_version."""

    def decorator(fn: _RollbackFn) -> _RollbackFn:
        _ROLLBACK_MIGRATIONS[to_version] = fn
        return fn

    return decorator


# --- Built-in migrations ---

@migration(0)
def _migrate_0_to_1(conn: sqlite3.Connection) -> None:
    """v0 → v1: Add indexes for performance."""
    conn.executescript("""
        CREATE INDEX IF NOT EXISTS idx_mem_kind ON memories(kind);
        CREATE INDEX IF NOT EXISTS idx_mem_source ON memories(source);
        CREATE INDEX IF NOT EXISTS idx_mem_valid_to ON memories(valid_to);
    """)


@migration(1)
def _migrate_1_to_2(conn: sqlite3.Connection) -> None:
    """v1 → v2: Add relations table if not exists."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS relations (
            id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            relation TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_rel_source ON relations(source_id);
        CREATE INDEX IF NOT EXISTS idx_rel_target ON relations(target_id);
    """)


# --- Built-in rollbacks ---

@rollback(0)
def _rollback_1_to_0(conn: sqlite3.Connection) -> None:
    """v1 → v0: Remove performance indexes added in migration 0."""
    conn.executescript("""
        DROP INDEX IF EXISTS idx_mem_kind;
        DROP INDEX IF EXISTS idx_mem_source;
        DROP INDEX IF EXISTS idx_mem_valid_to;
    """)
    conn.commit()


@rollback(1)
def _rollback_2_to_1(conn: sqlite3.Connection) -> None:
    """v2 → v1: Remove relations table added in migration 1."""
    conn.executescript("""
        DROP INDEX IF EXISTS idx_rel_source;
        DROP INDEX IF EXISTS idx_rel_target;
        DROP TABLE IF EXISTS relations;
    """)
    conn.commit()


class MigrationRunner:
    """Run schema migrations on a SQLite database."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)

    def _get_version(self, conn: sqlite3.Connection) -> int:
        """Get the current schema version, or 0 if not tracked."""
        try:
            row = conn.execute("SELECT version FROM _schema_version ORDER BY applied_at DESC LIMIT 1").fetchone()
            return row[0] if row else 0
        except sqlite3.OperationalError:
            return 0

    def _set_version(self, conn: sqlite3.Connection, version: int) -> None:
        """Record a new schema version."""
        conn.execute(
            "CREATE TABLE IF NOT EXISTS _schema_version (version INTEGER, applied_at TEXT)"
        )
        conn.execute(
            "INSERT INTO _schema_version (version, applied_at) VALUES (?, ?)",
            (version, datetime.now(UTC).isoformat()),
        )
        conn.commit()

    def run_migrations(self) -> int:
        """Run all pending migrations. Returns the final version."""
        with sqlite3.connect(self.db_path) as conn:
            version = self._get_version(conn)
            if version >= CURRENT_VERSION:
                logger.debug("Schema already at version %d", version)
                return version
            for v in range(version, CURRENT_VERSION):
                fn = _MIGRATIONS.get(v)
                if fn is None:
                    logger.warning("No migration from version %d", v)
                    break
                logger.info("Migrating schema %d → %d", v, v + 1)
                fn(conn)
                self._set_version(conn, v + 1)
            return self._get_version(conn)

    def rollback(self, version: int) -> int:
        """Roll back the schema to *version*, reversing migrations in order.

        Reverses each migration step from the current version down to *version*.
        If no rollback exists for a step, raises a clear ``ValueError``.
        Returns the resulting schema version after rollback.
        """
        with sqlite3.connect(self.db_path) as conn:
            current = self._get_version(conn)
            if current <= version:
                logger.debug("Schema already at or below version %d", version)
                return current
            for v in range(current, version, -1):
                fn = _ROLLBACK_MIGRATIONS.get(v - 1)
                if fn is None:
                    raise ValueError(
                        f"No rollback registered for migration to version {v} "
                        f"(cannot reverse {v} → {v - 1})"
                    )
                logger.info("Rolling back schema %d → %d", v, v - 1)
                fn(conn)
                self._set_version(conn, v - 1)
            return self._get_version(conn)


def backup_database(db_path: Path, backup_dir: Path, max_backups: int = 5) -> Path | None:
    """Create a timestamped backup of a SQLite database.

    Keeps at most ``max_backups`` backups, deleting the oldest.
    Returns the backup path, or None if the source doesn't exist.
    """
    if not db_path.exists():
        return None
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"{db_path.stem}_backup_{timestamp}.db"
    shutil.copy2(db_path, backup_path)

    # Retention: keep only the latest max_backups
    backups = sorted(backup_dir.glob(f"{db_path.stem}_backup_*.db"))
    if len(backups) > max_backups:
        for old in backups[:-max_backups]:
            old.unlink()
    return backup_path
