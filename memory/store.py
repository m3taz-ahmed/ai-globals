#!/usr/bin/env python3
"""Temporal memory store with episodic/semantic/fact layers."""

from __future__ import annotations

import json
import re
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, ClassVar

import config
from runtime.repository import BaseRepository

from .hybrid import HybridSearcher
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


class MemoryStore(BaseRepository):
    """SQLite-backed memory with temporal validity, graph relations, and optional vector index."""

    _schema_sql: ClassVar[list[str]] = [
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
        """,
        """
        CREATE TABLE IF NOT EXISTS relations (
            id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            relation TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """,
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
            content, content_rowid=rowid, content='memories'
        )
        """,
        """
        CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories
        BEGIN
            INSERT INTO memories_fts(rowid, content) VALUES (new.rowid, new.content);
        END
        """,
        """
        CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories
        BEGIN
            INSERT INTO memories_fts(memories_fts, rowid, content) VALUES('delete', old.rowid, old.content);
        END
        """,
        """
        CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories
        BEGIN
            INSERT INTO memories_fts(memories_fts, rowid, content) VALUES('delete', old.rowid, old.content);
            INSERT INTO memories_fts(rowid, content) VALUES (new.rowid, new.content);
        END
        """,
    ]
    _index_sql: ClassVar[list[str]] = [
        "CREATE INDEX IF NOT EXISTS idx_mem_kind ON memories(kind)",
        "CREATE INDEX IF NOT EXISTS idx_mem_source ON memories(source)",
        "CREATE INDEX IF NOT EXISTS idx_mem_valid_to ON memories(valid_to)",
        "CREATE INDEX IF NOT EXISTS idx_rel_source ON relations(source_id)",
        "CREATE INDEX IF NOT EXISTS idx_rel_target ON relations(target_id)",
    ]

    def __init__(self, root: Path | None = None, db_path: Path | None = None, enable_vector: bool = True) -> None:
        self.root = root or config.discover_root()
        self.vector = VectorMemory(self.root) if enable_vector else None
        super().__init__(db_path or self.root / "brain" / "memory.db")

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

    _MAX_FTS_TOKEN_LEN: int = 64

    def _fts_query(self, query: str) -> str:
        """Sanitize a query for FTS5 MATCH by quoting each token.

        Escapes double quotes, removes FTS5 boolean operators and wildcards,
        and caps token length to avoid injection and long queries.
        """
        tokens = query.split()
        if not tokens:
            return '""'
        sanitized = []
        for token in tokens:
            token = re.sub(r'["*]', "", token)
            token = re.sub(r"\b(AND|OR|NOT)\b", "", token, flags=re.IGNORECASE)
            token = token[: self._MAX_FTS_TOKEN_LEN]
            if token:
                sanitized.append(f'"{token}"')
        return " ".join(sanitized) if sanitized else '""'

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

    # Whitelist of allowed filter columns to prevent SQL injection in dynamic WHERE clauses.
    _ALLOWED_FILTER_COLUMNS: frozenset[str] = frozenset({"kind", "source"})

    def search_vector(
        self, query: str, k: int = 5, kind: str | None = None, source: str | None = None
    ) -> list[dict[str, Any]]:
        """Search using vector index, optionally filtered by kind/source and temporal validity."""
        if not self.vector or not self.vector.is_available():
            return []
        ids: list[str] | None = None
        if kind or source:
            now = datetime.now(timezone.utc).isoformat()
            # Build WHERE from whitelisted condition templates only â€” no f-string interpolation
            # of user values into SQL. All values passed as parameterized placeholders.
            conditions: list[str] = ["(valid_to IS NULL OR valid_to > ?)"]
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

    def search_hybrid(
        self, query: str, k: int = 5, kind: str | None = None,
        source: str | None = None, explain: bool = False
    ) -> list[dict[str, Any]]:
        """Hybrid search combining FTS, vector, and entity boosting."""
        if not self.vector or not self.vector.is_available():
            return [
                {"id": m.id, "kind": m.kind, "source": m.source,
                 "content": m.content, "score": None}
                for m in self.search(query, kind=kind, limit=k)
            ]
        return HybridSearcher(self).search(
            query, k=k, kind=kind, source=source, explain=explain)

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
        # Validate all sources are strings to prevent placeholder manipulation.
        for src in sources:
            if not isinstance(src, str) or not src:
                raise ValueError(f"Invalid source for deletion: {src!r}")
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

    def count(self) -> int:
        """Return total number of memories (including invalidated)."""
        with self._conn() as conn:
            row = conn.execute("SELECT COUNT(*) as cnt FROM memories").fetchone()
        return int(row["cnt"]) if row else 0

    def list_all(self, kind: str | None = None, limit: int = 1000) -> list[Memory]:
        """List memories, optionally filtered by kind, most recent first."""
        with self._conn() as conn:
            if kind:
                rows = conn.execute(
                    "SELECT * FROM memories WHERE kind = ? ORDER BY created_at DESC LIMIT ?",
                    (kind, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM memories ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [self._row_to_memory(row) for row in rows]

    def delete_hard(self, mem_id: str) -> bool:
        """Hard-delete a memory by ID (removes row + vector). Returns True if existed."""
        with self._conn() as conn:
            cur = conn.execute("DELETE FROM memories WHERE id = ?", (mem_id,))
            existed = cur.rowcount > 0
        if existed and self.vector and self.vector.is_available():
            self.vector.remove(mem_id)
        return existed
