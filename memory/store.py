#!/usr/bin/env python3
"""Temporal memory store with episodic/semantic/fact layers."""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import config

from .vector import VectorMemory


@dataclass
class Memory:
    id: str
    kind: str  # episodic | semantic | factual | procedural
    content: str
    source: str
    meta: str
    created_at: str
    valid_from: str
    valid_to: str | None


class MemoryStore:
    """SQLite-backed memory with temporal validity, graph relations, and optional vector index."""

    def __init__(self, root: Path | None = None, db_path: Path | None = None, enable_vector: bool = True) -> None:
        self.root = root or config.discover_root()
        self.db_path = db_path or self.root / "brain" / "memory.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.vector = VectorMemory(self.root) if enable_vector else None
        self._init_schema()

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source TEXT,
                    meta TEXT,
                    created_at TEXT NOT NULL,
                    valid_from TEXT NOT NULL,
                    valid_to TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS relations (
                    id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    relation TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_mem_kind ON memories(kind)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_rel_source ON relations(source_id)"
            )
            conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                    content, content_rowid=rowid, content='memories'
                )
                """
            )
            conn.execute(
                """
                CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories
                BEGIN
                    INSERT INTO memories_fts(rowid, content) VALUES (new.rowid, new.content);
                END
                """
            )
            conn.execute(
                """
                CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories
                BEGIN
                    INSERT INTO memories_fts(memories_fts, rowid, content) VALUES('delete', old.rowid, old.content);
                END
                """
            )
            conn.execute(
                """
                CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories
                BEGIN
                    INSERT INTO memories_fts(memories_fts, rowid, content) VALUES('delete', old.rowid, old.content);
                    INSERT INTO memories_fts(rowid, content) VALUES (new.rowid, new.content);
                END
                """
            )

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def add(
        self,
        kind: str,
        content: str,
        source: str = "",
        meta: dict[str, Any] | None = None,
        valid_to: str | None = None,
    ) -> Memory:
        now = datetime.now(timezone.utc).isoformat()
        mem = Memory(
            id=str(uuid.uuid4()),
            kind=kind,
            content=content,
            source=source,
            meta=json.dumps(meta or {}),
            created_at=now,
            valid_from=now,
            valid_to=valid_to,
        )
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO memories (id, kind, content, source, meta, created_at, valid_from, valid_to)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (mem.id, mem.kind, mem.content, mem.source, mem.meta, mem.created_at, mem.valid_from, mem.valid_to),
            )
        if self.vector and self.vector.is_available():
            self.vector.add(mem.id, content)
        return mem

    def _escape_like(self, value: str) -> str:
        return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    def _fts_query(self, query: str) -> str:
        """Sanitize a query for FTS5 MATCH by quoting each token."""
        tokens = query.split()
        if not tokens:
            return '""'
        return " ".join(f'"{token.replace(chr(34), chr(34) + chr(34))}"' for token in tokens)

    def search(self, query: str, kind: str | None = None, limit: int = 10) -> list[Memory]:
        """Search memory using FTS5 and optional kind filter."""
        q = self._fts_query(query)
        with self._conn() as conn:
            if kind:
                rows = conn.execute(
                    """
                    SELECT m.* FROM memories m
                    JOIN memories_fts fts ON m.rowid = fts.rowid
                    WHERE m.kind = ? AND memories_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                    """,
                    (kind, q, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT m.* FROM memories m
                    JOIN memories_fts fts ON m.rowid = fts.rowid
                    WHERE memories_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                    """,
                    (q, limit),
                ).fetchall()
        return [self._row_to_memory(row) for row in rows]

    def get(self, mem_id: str) -> Memory | None:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM memories WHERE id = ?", (mem_id,)).fetchone()
        return self._row_to_memory(row) if row else None

    def search_vector(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        """Search using vector index (requires sentence-transformers + turbovec)."""
        if not self.vector or not self.vector.is_available():
            return []
        return self.vector.search(query, k=k)

    def relate(self, source_id: str, target_id: str, relation: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO relations (id, source_id, target_id, relation, created_at) VALUES (?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), source_id, target_id, relation, now),
            )

    def related(self, mem_id: str, relation: str | None = None) -> list[tuple[Memory, str]]:
        with self._conn() as conn:
            if relation:
                rows = conn.execute(
                    "SELECT m.*, r.relation FROM relations r JOIN memories m ON m.id = r.target_id WHERE r.source_id = ? AND r.relation = ?",
                    (mem_id, relation),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT m.*, r.relation FROM relations r JOIN memories m ON m.id = r.target_id WHERE r.source_id = ?",
                    (mem_id,),
                ).fetchall()
        result = []
        for row in rows:
            mem = self._row_to_memory(row)
            result.append((mem, row["relation"]))
        return result

    def _row_to_memory(self, row: sqlite3.Row) -> Memory:
        return Memory(
            id=row["id"],
            kind=row["kind"],
            content=row["content"],
            source=row["source"],
            meta=row["meta"],
            created_at=row["created_at"],
            valid_from=row["valid_from"],
            valid_to=row["valid_to"],
        )

    def delete_by_source(self, source: str) -> None:
        if not source:
            return
        with self._conn() as conn:
            rows = conn.execute("SELECT id FROM memories WHERE source = ?", (source,)).fetchall()
            if not rows:
                return
            mem_ids = [row["id"] for row in rows]
            conn.execute("DELETE FROM memories WHERE source = ?", (source,))
        if self.vector and self.vector.is_available():
            for mem_id in mem_ids:
                self.vector.remove(mem_id)

    def invalidate(self, mem_id: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            conn.execute("UPDATE memories SET valid_to = ? WHERE id = ?", (now, mem_id))
