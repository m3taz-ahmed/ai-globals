#!/usr/bin/env python3
"""Base repository for SQLite-backed state stores.

Provides a unified connection management pattern with WAL mode, busy timeout,
thread-safe locking, and transactional context managers. Subclasses define
their schema via ``_schema_sql`` and implement domain-specific queries.
"""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import ClassVar


class BaseRepository:
    """Base class for SQLite-backed repositories with thread-safe connections.

    Subclasses must set ``_schema_sql`` (a list of CREATE TABLE statements)
    and optionally override ``_index_sql`` for additional indexes.
    """

    _schema_sql: ClassVar[list[str]] = []
    _index_sql: ClassVar[list[str]] = []

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_schema()

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        """Yield a SQLite connection with WAL mode and busy timeout.

        Commits on success, rolls back on exception, always closes.
        Thread-safe via RLock.
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def _init_schema(self) -> None:
        """Create tables and indexes if they don't exist."""
        with self._conn() as conn:
            for sql in self._schema_sql:
                conn.execute(sql)
            for sql in self._index_sql:
                conn.execute(sql)

    def vacuum(self) -> None:
        """Reclaim unused space in the database file."""
        with self._conn() as conn:
            conn.execute("VACUUM")
