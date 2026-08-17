"""Tests for runtime/repository.py — base SQLite repository."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import pytest

from runtime.repository import BaseRepository


class _TestRepo(BaseRepository):
    """Concrete subclass for testing."""

    _schema_sql: ClassVar[list[str]] = [
        "CREATE TABLE IF NOT EXISTS items (id TEXT PRIMARY KEY, value TEXT)",
    ]
    _index_sql: ClassVar[list[str]] = [
        "CREATE INDEX IF NOT EXISTS idx_items_value ON items(value)",
    ]

    def insert(self, item_id: str, value: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO items (id, value) VALUES (?, ?)", (item_id, value)
            )

    def insert_failing(self, item_id: str, value: str) -> None:
        """Insert that deliberately raises to trigger rollback."""
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO items (id, value) VALUES (?, ?)", (item_id, value)
            )
            raise RuntimeError("deliberate failure")

    def count(self) -> int:
        with self._conn() as conn:
            row = conn.execute("SELECT COUNT(*) FROM items").fetchone()
            return row[0]


class TestBaseRepository:
    def test_schema_initialized(self, tmp_path: Path) -> None:
        repo = _TestRepo(tmp_path / "test.db")
        assert repo.count() == 0

    def test_insert_and_query(self, tmp_path: Path) -> None:
        repo = _TestRepo(tmp_path / "test.db")
        repo.insert("a", "hello")
        assert repo.count() == 1

    def test_rollback_on_exception(self, tmp_path: Path) -> None:
        """Cover lines 50-52: exception in _conn context triggers rollback."""
        repo = _TestRepo(tmp_path / "test.db")
        with pytest.raises(RuntimeError, match="deliberate failure"):
            repo.insert_failing("a", "hello")
        # The insert should have been rolled back
        assert repo.count() == 0

    def test_vacuum(self, tmp_path: Path) -> None:
        """Cover lines 66-67: vacuum reclaims unused space."""
        repo = _TestRepo(tmp_path / "test.db")
        repo.insert("a", "hello")
        repo.insert("b", "world")
        # Vacuum should not raise
        repo.vacuum()
        assert repo.count() == 2

    def test_db_path_parent_created(self, tmp_path: Path) -> None:
        """Ensure parent directory is created if it doesn't exist."""
        nested = tmp_path / "nested" / "dir" / "test.db"
        _TestRepo(nested)
        assert nested.parent.exists()
