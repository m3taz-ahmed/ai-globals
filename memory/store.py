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
        self.add_batch([mem])
        return mem

    def add_batch(self, memories: list[Memory]) -> list[Memory]:
        """Insert a batch of memories in a single SQLite transaction and vector index write."""
        if not memories:
            return []
        rows = [
            (m.id, m.kind, m.content, m.source, m.meta, m.created_at, m.valid_from, m.valid_to)
            for m in memories
        ]
        with self._conn() as conn:
            conn.executemany(
                """
                INSERT INTO memories (id, kind, content, source, meta, created_at, valid_from, valid_to)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
        if self.vector and self.vector.is_available():
            self.vector.add_batch([m.id for m in memories], [m.content for m in memories])
        return memories

    def _fts_query(self, query: str) -> str:
        """Sanitize a query for FTS5 MATCH by quoting each token."""
        tokens = query.split()
        if not tokens:
            return '""'
        return " ".join(f'"{token.replace(chr(34), chr(34) + chr(34))}"' for token in tokens)

    def search(self, query: str, kind: str | None = None, limit: int = 10) -> list[Memory]:
        """Search memory using FTS5 and optional kind filter; excludes invalidated memories."""
        q = self._fts_query(query)
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            if kind:
                rows = conn.execute(
                    """
                    SELECT m.* FROM memories m
                    JOIN memories_fts fts ON m.rowid = fts.rowid
                    WHERE m.kind = ? AND memories_fts MATCH ?
                        AND (m.valid_to IS NULL OR m.valid_to > ?)
                    ORDER BY rank
                    LIMIT ?
                    """,
                    (kind, q, now, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT m.* FROM memories m
                    JOIN memories_fts fts ON m.rowid = fts.rowid
                    WHERE memories_fts MATCH ?
                        AND (m.valid_to IS NULL OR m.valid_to > ?)
                    ORDER BY rank
                    LIMIT ?
                    """,
                    (q, now, limit),
                ).fetchall()
        return [self._row_to_memory(row) for row in rows]

    def get(self, mem_id: str) -> Memory | None:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM memories WHERE id = ?", (mem_id,)).fetchone()
        return self._row_to_memory(row) if row else None

    def search_vector(
        self, query: str, k: int = 5, kind: str | None = None, source: str | None = None
    ) -> list[dict[str, Any]]:
        """Search using vector index, optionally filtered by kind/source and temporal validity."""
        if not self.vector or not self.vector.is_available():
            return []
        ids: list[str] | None = None
        if kind or source:
            now = datetime.now(timezone.utc).isoformat()
            conditions = ["(valid_to IS NULL OR valid_to > ?)"]
            params: list[Any] = [now]
            if kind:
                conditions.append("kind = ?")
                params.append(kind)
            if source:
                conditions.append("source = ?")
                params.append(source)
            where = " AND ".join(conditions)
            with self._conn() as conn:
                rows = conn.execute(f"SELECT id FROM memories WHERE {where}", params).fetchall()
            ids = [row["id"] for row in rows]
            if not ids:
                return []
        return self.vector.search(query, k=k, ids=ids)

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
        self.delete_by_source_batch([source])

    def delete_by_source_batch(self, sources: list[str]) -> list[str]:
        """Delete all memories for a list of sources and remove their vectors and relations in one batch."""
        if not sources:
            return []
        placeholders = ",".join("?" for _ in sources)
        mem_ids: list[str] = []
        with self._conn() as conn:
            rows = conn.execute(
                f"SELECT id FROM memories WHERE source IN ({placeholders})", sources
            ).fetchall()
            mem_ids = [row["id"] for row in rows]
            if mem_ids:
                id_placeholders = ",".join("?" for _ in mem_ids)
                conn.execute(
                    f"DELETE FROM relations WHERE source_id IN ({id_placeholders}) OR target_id IN ({id_placeholders})",
                    mem_ids + mem_ids,
                )
            conn.execute(f"DELETE FROM memories WHERE source IN ({placeholders})", sources)
        if self.vector and self.vector.is_available() and mem_ids:
            self.vector.remove_batch(mem_ids)
        return mem_ids

    def invalidate(self, mem_id: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            conn.execute("UPDATE memories SET valid_to = ? WHERE id = ?", (now, mem_id))
        if self.vector and self.vector.is_available():
            self.vector.remove(mem_id)
