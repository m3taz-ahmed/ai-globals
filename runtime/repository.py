#!/usr/bin/env python3
"""Base repository for SQLite-backed state stores.

Provides a unified connection management pattern with WAL mode, busy timeout,
thread-safe locking, and transactional context managers. Subclasses define
their schema via ``_schema_sql`` and implement domain-specific queries.
"""

from __future__ import annotations

import contextlib
import queue
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

    A simple connection pool reuses SQLite connections across calls to avoid
    repeated connect/close overhead. Pool size is configurable via
    ``_pool_size`` (default 5).
    """

    _schema_sql: ClassVar[list[str]] = []
    _index_sql: ClassVar[list[str]] = []
    _pool_size: ClassVar[int] = 5

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._pool: queue.Queue[sqlite3.Connection | None] = queue.Queue(
            maxsize=self._pool_size
        )
        self._init_schema()

    def _create_conn(self) -> sqlite3.Connection:
        """Create a new SQLite connection with WAL mode and busy timeout."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        """Yield a SQLite connection from the pool.

        Connections are created on demand up to ``_pool_size``. On exit the
        connection is returned to the pool (not closed). Commits on success,
        rolls back on exception. Thread-safe via RLock.
        """
        conn: sqlite3.Connection | None = None
        with self._lock:
            try:
                conn = self._pool.get_nowait()
            except queue.Empty:
                conn = None
            if conn is None:
                conn = self._create_conn()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            with self._lock, contextlib.suppress(queue.Full):
                self._pool.put_nowait(conn)

    def _init_schema(self) -> None:
        """Create tables and indexes if they don't exist."""
        with self._conn() as conn:
            for sql in self._schema_sql:
                conn.execute(sql)
            for sql in self._index_sql:
                conn.execute(sql)

    def close(self) -> None:
        """Close any persistent resources. Base implementation is a no-op
        since ``_conn()`` opens/closes per-call. Subclasses with persistent
        connections should override.
        """
        return None

    def close_all(self) -> None:
        """Close all pooled connections."""
        with self._lock:
            while True:
                try:
                    conn = self._pool.get_nowait()
                except queue.Empty:
                    break
                if conn is not None:
                    conn.close()

    def vacuum(self) -> None:
        """Reclaim unused space in the database file."""
        with self._conn() as conn:
            conn.execute("VACUUM")
