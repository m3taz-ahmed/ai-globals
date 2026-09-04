#!/usr/bin/env python3
"""Temporal memory store with episodic/semantic/fact layers."""

from __future__ import annotations

import contextlib
import hmac
import json
import logging
import os
import re
import secrets
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, ClassVar

import config
from runtime.repository import (
    BaseRepository,  # LAYERING NOTE: memory→runtime cross-layer dep; tracked for refactor
)

from .hybrid import HybridSearcher
from .schema_contract import verify_schema_integrity
from .vector import VectorMemory

logger = logging.getLogger(__name__)

# Identity keys that must NOT be set via caller metadata (from mem0).
# These are security-sensitive: allowing callers to set them via metadata
# enables tenant-scoping attacks where malicious metadata places memories
# into unauthorized scopes.
_IDENTITY_KEYS: frozenset[str] = frozenset({
    "user_id", "agent_id", "run_id", "session_id", "tenant_id", "actor_id",
})

# ---------------------------------------------------------------------------
# Integrity (OWASP ASI06 — Memory Poisoning defense)
# ---------------------------------------------------------------------------
# Every memory entry is signed with HMAC-SHA256 over a canonical representation
# of its core content. The signing key is derived from the AIZEE_INTEGRITY_KEY
# environment variable when present, otherwise from a per-root key file
# (state/integrity.key) generated on first use. Signing is additive: legacy
# entries without a signature are still loaded, just flagged as "unsigned".

_INTEGRITY_KEY_ENV = "AIZEE_INTEGRITY_KEY"
_INTEGRITY_KEY_RELATIVE = Path("state") / "integrity.key"


def _integrity_canonical(
    content: str,
    kind: str,
    source: str,
    meta: str,
    created_at: str,
) -> str:
    """Build the canonical, deterministic signing payload for a memory entry."""
    return json.dumps(
        {
            "content": content,
            "kind": kind,
            "source": source,
            "meta": meta,
            "created_at": created_at,
        },
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _sign_memory(
    content: str,
    kind: str,
    source: str,
    meta: str,
    created_at: str,
    key: str,
) -> str:
    """Compute the HMAC-SHA256 integrity signature for a memory entry."""
    payload = _integrity_canonical(content, kind, source, meta, created_at).encode("utf-8")
    return hmac.new(key.encode("utf-8"), payload, sha256).hexdigest()


def _deterministic_id(
    content: str,
    kind: str,
    source: str = "",
    user_id: str | None = None,
    agent_id: str | None = None,
    session_id: str | None = None,
) -> str:
    """WS-F W1: Generate a deterministic ID from content hash.

    Uses SHA-256 of (kind, source, tenant ids, content) to produce a stable
    ID. Tenant ids are part of the hash so user B re-adding user A's content
    gets a distinct row (no cross-tenant collision / stale valid_to return).
    """
    h = sha256(f"{kind}|{source}|{user_id or ''}|{agent_id or ''}|{session_id or ''}|{content}".encode()).hexdigest()[:16]
    return f"mem_{h}"


def _extract_facts(content: str) -> list[str]:
    """WS-F W3: Extract simple facts from content.

    Extracts sentences that look like factual statements (contain a verb
    and a subject). This is a lightweight heuristic — not a full NLP
    pipeline. Returns a list of fact strings.
    """
    # Split into sentences
    sentences = re.split(r"[.!?]+", content)
    facts: list[str] = []
    # Simple heuristic: sentences with 5+ words that contain a copula or
    # common verbs are likely factual statements
    _verbs = {"is", "are", "was", "were", "has", "have", "uses",
              "requires", "depends", "contains", "includes", "supports"}
    for s in sentences:
        s = s.strip()
        if len(s.split()) < 5:
            continue
        words = set(s.lower().split())
        if words & _verbs:
            facts.append(s)
    return facts


def _strip_identity_keys(metadata: dict[str, Any]) -> dict[str, Any]:
    """Remove identity keys from caller metadata (from mem0 security pattern).

    Prevents tenant-scoping attacks where malicious metadata could place
    memories into unauthorized scopes. Identity keys must be passed as
    explicit parameters, not buried in metadata.
    """
    return {k: v for k, v in metadata.items() if k not in _IDENTITY_KEYS}


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
    integrity_sig: str | None = None  # HMAC-SHA256 over canonical content
    integrity: str = "unsigned"  # ok | tampered | unsigned


class _DecayHelper:
    """Decay-scoring helpers extracted from MemoryStore (CODE-03)."""

    _decay_table_sql: ClassVar[list[str]] = [
        """
        CREATE TABLE IF NOT EXISTS memory_decay (
            mem_id TEXT PRIMARY KEY,
            decay_score REAL NOT NULL DEFAULT 1.0,
            last_accessed TEXT NOT NULL,
            access_count INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (mem_id) REFERENCES memories(id) ON DELETE CASCADE
        )
        """,
    ]

    def __init__(self, store: MemoryStore) -> None:
        self._store = store

    def _ensure_decay_table(self) -> None:
        """Create the decay table if it doesn't exist (W5)."""
        with self._store._conn() as conn:
            for sql in self._decay_table_sql:
                conn.execute(sql)

    def record_access(self, mem_id: str) -> None:
        """WS-F W5: Record an access event for decay scoring.

        Updates the decay table: increments access count and updates
        last_accessed timestamp. Creates the row if it doesn't exist.
        """
        self._ensure_decay_table()
        now = datetime.now(timezone.utc).isoformat()
        with self._store._conn() as conn:
            conn.execute(
                """
                INSERT INTO memory_decay (mem_id, decay_score, last_accessed, access_count)
                VALUES (?, 1.0, ?, 1)
                ON CONFLICT(mem_id) DO UPDATE SET
                    access_count = access_count + 1,
                    last_accessed = ?,
                    decay_score = MIN(1.0, decay_score + 0.1)
                """,
                (mem_id, now, now),
            )

    def get_decay_score(self, mem_id: str) -> float:
        """WS-F W5: Get the decay score for a memory (0.0-1.0).

        Returns 1.0 if no decay tracking exists (new or untracked memory).
        """
        self._ensure_decay_table()
        with self._store._conn() as conn:
            row = conn.execute(
                "SELECT decay_score FROM memory_decay WHERE mem_id = ?",
                (mem_id,),
            ).fetchone()
        return float(row["decay_score"]) if row else 1.0

    def apply_decay(self, decay_rate: float = 0.01) -> int:
        """WS-F W5: Apply time-based decay to all tracked memories.

        Reduces decay_score by decay_rate for all memories. Memories that
        haven't been accessed recently decay faster. Returns the number
        of memories updated.
        """
        self._ensure_decay_table()
        with self._store._conn() as conn:
            cur = conn.execute(
                """
                UPDATE memory_decay
                SET decay_score = MAX(0.0, decay_score - ?)
                WHERE decay_score > 0.0
                """,
                (decay_rate,),
            )
            return cur.rowcount


class _SearchHelper:
    """Search helpers extracted from MemoryStore (CODE-03)."""

    _MAX_FTS_TOKEN_LEN: int = 64

    def __init__(self, store: MemoryStore) -> None:
        self._store = store

    def _fts_query(self, query: str) -> str:
        """Sanitize a query for FTS5 MATCH by quoting each token.

        Escapes double quotes, removes FTS5 boolean operators and wildcards,
        and caps token length to avoid injection and long queries.
        Returns "" when nothing searchable remains (callers must skip MATCH).
        """
        tokens = query.split()
        if not tokens:
            return ""
        sanitized = []
        for token in tokens:
            token = re.sub(r'["*()\-]', "", token)
            token = re.sub(r"\b(AND|OR|NOT)\b", "", token, flags=re.IGNORECASE)
            token = token[: self._MAX_FTS_TOKEN_LEN]
            if token:
                sanitized.append(f'"{token}"')
        return " ".join(sanitized)

    def search(self, query: str, kind: str | None = None, limit: int = 10) -> list[Memory]:
        """Search memory using FTS5 and optional kind filter; excludes invalidated memories."""
        q = self._fts_query(query)
        if not q:
            return []
        now = datetime.now(timezone.utc).isoformat()
        with self._store._conn() as conn:
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
        return [self._store._row_to_memory(row) for row in rows]

    def search_vector(
        self, query: str, k: int = 5, kind: str | None = None, source: str | None = None
    ) -> list[dict[str, Any]]:
        """Search using vector index, optionally filtered by kind/source and temporal validity."""
        if not self._store.vector or not self._store.vector.is_available():
            return []
        ids: list[str] | None = None
        if kind or source:
            now = datetime.now(timezone.utc).isoformat()
            conditions: list[str] = ["(valid_to IS NULL OR valid_to > ?)"]
            params: list[Any] = [now]
            if kind:
                conditions.append("kind = ?")
                params.append(kind)
            if source:
                conditions.append("source = ?")
                params.append(source)
            where = " AND ".join(conditions)
            with self._store._conn() as conn:
                # Capped allowlist: unbounded id lists blow up vector-search
                # memory on large DBs. Most-recent-first keeps it relevant.
                rows = conn.execute(
                    f"SELECT id FROM memories WHERE {where} ORDER BY created_at DESC LIMIT 10000",
                    params,
                ).fetchall()
            ids = [row["id"] for row in rows]
            if not ids:
                return []
        return self._store.vector.search(query, k=k, ids=ids)

    def search_hybrid(
        self, query: str, k: int = 5, kind: str | None = None,
        source: str | None = None, explain: bool = False
    ) -> list[dict[str, Any]]:
        """Hybrid search combining FTS, vector, and entity boosting."""
        if not self._store.vector or not self._store.vector.is_available():
            return [
                {"id": m.id, "kind": m.kind, "source": m.source,
                 "content": m.content, "score": None}
                for m in self.search(query, kind=kind, limit=k)
            ]
        return HybridSearcher(self._store).search(
            query, k=k, kind=kind, source=source, explain=explain)

    def _temporal_sql(
        self, start: str, end: str, kind: str | None, limit: int
    ) -> tuple[str, list[Any]]:
        """Build the SQL query and params for temporal range search."""
        now = datetime.now(timezone.utc).isoformat()
        if kind:
            sql = (
                "SELECT * FROM memories "
                "WHERE valid_from >= ? AND valid_from <= ? "
                "AND kind = ? "
                "AND (valid_to IS NULL OR valid_to > ?) "
                "ORDER BY valid_from DESC LIMIT ?"
            )
            return sql, [start, end, kind, now, limit]
        sql = (
            "SELECT * FROM memories "
            "WHERE valid_from >= ? AND valid_from <= ? "
            "AND (valid_to IS NULL OR valid_to > ?) "
            "ORDER BY valid_from DESC LIMIT ?"
        )
        return sql, [start, end, now, limit]

    def search_temporal(
        self,
        start: str,
        end: str,
        kind: str | None = None,
        limit: int = 50,
    ) -> list[Memory]:
        """WS-F W4: Search memories by temporal range.

        Returns memories whose valid_from falls within [start, end].
        Both bounds are ISO-8601 strings.
        """
        sql, params = self._temporal_sql(start, end, kind, limit)
        with self._store._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._store._row_to_memory(row) for row in rows]

    def search_safe(
        self, query: str, kind: str | None = None, limit: int = 10
    ) -> list[Memory]:
        """WS-F W6: Hardened search with additional sanitization.

        Wraps the standard search with:
        - Input length limiting (max 500 chars)
        - Null byte removal
        - SQL keyword stripping (extra defense beyond FTS5 sanitization)
        - Result count limiting (max 100)
        """
        if len(query) > 500:
            query = query[:500]
        query = re.sub(r"[\x00-\x1f]", "", query)
        query = re.sub(r"\b(DROP|DELETE|INSERT|UPDATE|ALTER|CREATE|EXEC)\b", "", query, flags=re.IGNORECASE)
        limit = min(limit, 100)
        return self.search(query, kind=kind, limit=limit)

    def count(self) -> int:
        """Return total number of memories (including invalidated)."""
        with self._store._conn() as conn:
            row = conn.execute("SELECT COUNT(*) as cnt FROM memories").fetchone()
        return int(row["cnt"]) if row else 0

    def list_all(self, kind: str | None = None, limit: int = 1000) -> list[Memory]:
        """List memories, optionally filtered by kind, most recent first."""
        with self._store._conn() as conn:
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
        return [self._store._row_to_memory(row) for row in rows]


class _RelationHelper:
    """Graph relations + row conversion for MemoryStore."""

    def __init__(self, store: MemoryStore) -> None:
        self._store = store

    def relate(self, source_id: str, target_id: str, relation: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._store._conn() as conn:
            conn.execute(
                "INSERT INTO relations (id, source_id, target_id, relation, created_at) VALUES (?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), source_id, target_id, relation, now),
            )

    def related(self, mem_id: str, relation: str | None = None) -> list[tuple[Memory, str]]:
        with self._store._conn() as conn:
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
        return [(self.row_to_memory(row), row["relation"]) for row in rows]

    def row_to_memory(self, row: sqlite3.Row) -> Memory:
        try:
            raw_sig = row["integrity_sig"]
        except IndexError:
            raw_sig = None
        sig: str | None = raw_sig if raw_sig else None
        content = row["content"]
        kind = row["kind"]
        source = row["source"] or ""
        meta = row["meta"] or ""
        created_at = row["created_at"]
        if sig is None:
            integrity = "unsigned"
        else:
            expected = _sign_memory(
                content, kind, source, meta, created_at, self._store._integrity_key
            )
            integrity = "ok" if hmac.compare_digest(expected, sig) else "tampered"
        return Memory(
            id=row["id"], kind=kind, content=content,
            source=source, meta=row["meta"], created_at=created_at,
            valid_from=row["valid_from"], valid_to=row["valid_to"],
            integrity_sig=sig, integrity=integrity,
        )


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
            valid_to TEXT,
            integrity_sig TEXT
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
        """
        CREATE TABLE IF NOT EXISTS memory_decay (
            mem_id TEXT PRIMARY KEY,
            decay_score REAL NOT NULL DEFAULT 1.0,
            last_accessed TEXT NOT NULL,
            access_count INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (mem_id) REFERENCES memories(id) ON DELETE CASCADE
        )
        """,
    ]
    _index_sql: ClassVar[list[str]] = [
        "CREATE INDEX IF NOT EXISTS idx_mem_kind ON memories(kind)",
        "CREATE INDEX IF NOT EXISTS idx_mem_source ON memories(source)",
        "CREATE INDEX IF NOT EXISTS idx_mem_valid_to ON memories(valid_to)",
        "CREATE INDEX IF NOT EXISTS idx_mem_valid_from ON memories(valid_from)",
        "CREATE INDEX IF NOT EXISTS idx_mem_created_at ON memories(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_rel_source ON relations(source_id)",
        "CREATE INDEX IF NOT EXISTS idx_rel_target ON relations(target_id)",
        "CREATE INDEX IF NOT EXISTS idx_decay_last_accessed ON memory_decay(last_accessed)",
    ]

    def __init__(self, root: Path | None = None, db_path: Path | None = None, enable_vector: bool = True) -> None:
        self.root = root or config.discover_root()
        self.vector = VectorMemory(self.root) if enable_vector else None
        super().__init__(db_path or self.root / "brain" / "memory.db")
        self._decay = _DecayHelper(self)
        self._search = _SearchHelper(self)
        self._relations = _RelationHelper(self)
        # Load (or generate) the integrity signing key.
        self._integrity_key = self._load_integrity_key()
        # Auto-migrate legacy decay table (add ON DELETE CASCADE) without data loss.
        self._migrate_decay_table()
        # Additive migration: ensure the integrity_sig column exists on old DBs.
        self._ensure_integrity_column()
        # Additive schema-integrity check: warn on drift, never block init.
        self._verify_schema()

    def _load_integrity_key(self) -> str:
        """Resolve the HMAC key for memory signing.

        Key resolution order:
        1. ``AIZEE_INTEGRITY_KEY`` env var (production — key never touches disk).
        2. ``AIZEE_INTEGRITY_KEY_FILE`` env var (path outside OS root).
        3. ``state/integrity.key`` under the root (dev fallback — warns loudly).
        """
        env_key = os.environ.get(_INTEGRITY_KEY_ENV)
        if env_key:
            return env_key
        # Check for external key file (production: key outside OS root)
        ext_key_file = os.environ.get("AIZEE_INTEGRITY_KEY_FILE")
        if ext_key_file:
            ext_path = Path(ext_key_file)
            if ext_path.exists():
                existing = ext_path.read_text(encoding="utf-8").strip()
                if existing:
                    return existing
        key_path = self.root / _INTEGRITY_KEY_RELATIVE
        if key_path.exists():
            existing = key_path.read_text(encoding="utf-8").strip()
            if existing:
                return existing
        new_key = secrets.token_hex(32)
        key_path.parent.mkdir(parents=True, exist_ok=True)
        # L6: write the HMAC key with restrictive permissions (0o600) so other
        # users on shared Unix hosts cannot read it. On Windows the mode is
        # effectively ignored (ACLs apply), but chmod is harmless.
        key_path.write_text(new_key, encoding="utf-8")
        # L6: restrict key file permissions (best-effort; harmless on Windows).
        with contextlib.suppress(OSError):
            os.chmod(key_path, 0o600)
        logger.warning(
            "SECURITY: AIZEE_INTEGRITY_KEY not set — auto-generated key at %s "
            "INSIDE the OS root. For production, set AIZEE_INTEGRITY_KEY env var "
            "or AIZEE_INTEGRITY_KEY_FILE to a path outside the OS root.",
            key_path,
        )
        return new_key

    def _ensure_integrity_column(self) -> None:
        """Additively add the integrity_sig column to existing memories tables."""
        try:
            with self._conn() as conn:
                conn.execute(
                    "ALTER TABLE memories ADD COLUMN integrity_sig TEXT"
                )
        except sqlite3.OperationalError:
            # Column already exists — safe to ignore (SQLite ALTER has no IF NOT EXISTS).
            pass

    def _migrate_decay_table(self) -> None:
        """Migrate legacy memory_decay table to add ON DELETE CASCADE if missing."""
        try:
            with self._conn() as conn:
                row = conn.execute("SELECT sql FROM sqlite_master WHERE name='memory_decay'").fetchone()
                if row is None or row["sql"] is None:
                    return
                sql = row["sql"]
                if "ON DELETE CASCADE" in sql:
                    return
                # Recreate with new DDL preserving existing data
                conn.execute("ALTER TABLE memory_decay RENAME TO memory_decay_legacy")
                for ddl in _DecayHelper._decay_table_sql:
                    conn.execute(ddl)
                conn.execute(
                    "INSERT OR IGNORE INTO memory_decay (mem_id, decay_score, last_accessed, access_count) "
                    "SELECT mem_id, decay_score, last_accessed, access_count FROM memory_decay_legacy"
                )
                conn.execute("DROP TABLE memory_decay_legacy")
                logger.info("Migrated memory_decay table to add ON DELETE CASCADE")
        except Exception as exc:  # pragma: no cover - best effort
            logger.warning("Failed to migrate memory_decay table: %s", exc)

    def _verify_schema(self) -> None:
        """Warn (do not block) if the on-disk schema drifted from the contract."""
        try:
            is_valid, drift_desc = verify_schema_integrity(self.db_path)
            if not is_valid and drift_desc:
                logger.warning("Schema drift detected in %s: %s", self.db_path, drift_desc)
        except Exception as exc:  # pragma: no cover - defensive, never block init
            logger.warning("Schema integrity check failed for %s: %s", self.db_path, exc)

    def add(
        self,
        kind: str,
        content: str,
        source: str = "",
        meta: dict[str, Any] | None = None,
        valid_to: str | None = None,
        user_id: str | None = None,
        agent_id: str | None = None,
        session_id: str | None = None,
    ) -> Memory:
        """Add a memory with optional identity scoping.

        Identity keys (user_id, agent_id, session_id) are passed as explicit
        parameters and stored in metadata. Caller-provided metadata is
        stripped of identity keys to prevent tenant-scoping attacks (from mem0).

        WS-F W1: Uses deterministic IDs (content hash) instead of random UUIDs.
        WS-F W2: Deduplicates — if a memory with the same content already
            exists, returns the existing one instead of creating a duplicate.
        """
        mem_id = _deterministic_id(content, kind, source, user_id, agent_id, session_id)
        existing = self.get(mem_id)
        if existing is not None:
            return existing
        safe_meta = self._build_safe_meta(meta, user_id, agent_id, session_id, content)
        mem = self._build_memory(mem_id, kind, content, source, safe_meta, valid_to)
        self.add_batch([mem])
        return mem

    def _build_safe_meta(
        self,
        meta: dict[str, Any] | None,
        user_id: str | None,
        agent_id: str | None,
        session_id: str | None,
        content: str,
    ) -> dict[str, Any]:
        """Build sanitized metadata with identity keys and extracted facts."""
        safe_meta = _strip_identity_keys(meta or {})
        if user_id:
            safe_meta["user_id"] = user_id
        if agent_id:
            safe_meta["agent_id"] = agent_id
        if session_id:
            safe_meta["session_id"] = session_id
        facts = _extract_facts(content)
        if facts:
            safe_meta["extracted_facts"] = facts
        return safe_meta

    def _build_memory(
        self,
        mem_id: str,
        kind: str,
        content: str,
        source: str,
        safe_meta: dict[str, Any],
        valid_to: str | None,
    ) -> Memory:
        """Construct a Memory object from the given parameters."""
        now = datetime.now(timezone.utc).isoformat()
        meta_str = json.dumps(safe_meta)
        integrity_sig = _sign_memory(
            content, kind, source, meta_str, now, self._integrity_key
        )
        return Memory(
            id=mem_id,
            kind=kind,
            content=content,
            source=source,
            meta=meta_str,
            created_at=now,
            valid_from=now,
            valid_to=valid_to,
            integrity_sig=integrity_sig,
            integrity="ok",
        )

    def add_batch(self, memories: list[Memory]) -> list[Memory]:
        """Insert a batch of memories in a single SQLite transaction and vector index write."""
        if not memories:
            return []
        rows = []
        for m in memories:
            sig = m.integrity_sig
            if sig is None:
                sig = _sign_memory(
                    m.content, m.kind, m.source or "", m.meta or "", m.created_at,
                    self._integrity_key,
                )
            rows.append(
                (m.id, m.kind, m.content, m.source, m.meta, m.created_at,
                 m.valid_from, m.valid_to, sig)
            )
        with self._conn() as conn:
            # OR IGNORE: check-then-insert in add() races under concurrency;
            # the PK makes the second writer a silent no-op instead of an
            # IntegrityError crash.
            conn.executemany(
                """
                INSERT OR IGNORE INTO memories (id, kind, content, source, meta, created_at, valid_from, valid_to, integrity_sig)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
        if self.vector and self.vector.is_available():
            self.vector.add_batch([m.id for m in memories], [m.content for m in memories])
        return memories

    def _fts_query(self, query: str) -> str:
        return self._search._fts_query(query)

    def search(self, query: str, kind: str | None = None, limit: int = 10) -> list[Memory]:
        return self._search.search(query, kind=kind, limit=limit)

    def get(self, mem_id: str) -> Memory | None:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM memories WHERE id = ?", (mem_id,)).fetchone()
        return self._row_to_memory(row) if row else None

    def search_vector(
        self, query: str, k: int = 5, kind: str | None = None, source: str | None = None
    ) -> list[dict[str, Any]]:
        return self._search.search_vector(query, k=k, kind=kind, source=source)

    def search_hybrid(
        self, query: str, k: int = 5, kind: str | None = None,
        source: str | None = None, explain: bool = False
    ) -> list[dict[str, Any]]:
        return self._search.search_hybrid(query, k=k, kind=kind, source=source, explain=explain)

    def relate(self, source_id: str, target_id: str, relation: str) -> None:
        self._relations.relate(source_id, target_id, relation)

    def related(self, mem_id: str, relation: str | None = None) -> list[tuple[Memory, str]]:
        return self._relations.related(mem_id, relation)

    def _row_to_memory(self, row: sqlite3.Row) -> Memory:
        return self._relations.row_to_memory(row)

    def delete_by_source(self, source: str) -> None:
        self.delete_by_source_batch([source])

    def delete_by_source_batch(self, sources: list[str]) -> list[str]:
        """Delete all memories for a list of sources and remove their vectors and relations in one batch."""
        if not sources:
            return []
        # Validate all sources are strings to prevent placeholder manipulation.
        for src in sources:
            if not isinstance(src, str) or not src or len(src) > 1000:
                raise ValueError(f"Invalid source for deletion: {src!r}")
        placeholders = ",".join("?" for _ in sources)
        mem_ids: list[str] = []
        with self._conn() as conn:
            rows = conn.execute(
                f"SELECT id FROM memories WHERE source IN ({placeholders})", sources
            ).fetchall()
            mem_ids = [row["id"] for row in rows]
            # Chunk IN-lists (SQLite variable limit is 999 by default).
            for chunk in (mem_ids[i:i + 500] for i in range(0, len(mem_ids), 500)):
                id_placeholders = ",".join("?" for _ in chunk)
                conn.execute(
                    f"DELETE FROM relations WHERE source_id IN ({id_placeholders}) OR target_id IN ({id_placeholders})",
                    chunk + chunk,
                )
                # Explicit decay cleanup for existing DBs where FK cascade is NO ACTION
                conn.execute(
                    f"DELETE FROM memory_decay WHERE mem_id IN ({id_placeholders})",
                    chunk,
                )
            conn.execute(f"DELETE FROM memories WHERE source IN ({placeholders})", sources)
        if self.vector and self.vector.is_available() and mem_ids:
            self.vector.remove_batch(mem_ids)
        return mem_ids

    def invalidate(self, mem_id: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            conn.execute("UPDATE memories SET valid_to = ? WHERE id = ?", (now, mem_id))
            conn.execute("DELETE FROM memory_decay WHERE mem_id = ?", (mem_id,))
        if self.vector and self.vector.is_available():
            self.vector.remove(mem_id)

    def count(self) -> int:
        return self._search.count()

    def list_all(self, kind: str | None = None, limit: int = 1000) -> list[Memory]:
        return self._search.list_all(kind=kind, limit=limit)

    def delete_hard(self, mem_id: str) -> bool:
        """Hard-delete a memory by ID (removes row + vector). Returns True if existed."""
        with self._conn() as conn:
            # Explicit decay cleanup for existing DBs without CASCADE
            conn.execute("DELETE FROM memory_decay WHERE mem_id = ?", (mem_id,))
            cur = conn.execute("DELETE FROM memories WHERE id = ?", (mem_id,))
            existed = cur.rowcount > 0
        if existed and self.vector and self.vector.is_available():
            self.vector.remove(mem_id)
        return existed

    # --- WS-F W4: Temporal search ----------------------------------------

    def search_temporal(
        self,
        start: str,
        end: str,
        kind: str | None = None,
        limit: int = 50,
    ) -> list[Memory]:
        return self._search.search_temporal(start, end, kind=kind, limit=limit)

    # --- WS-F W5: Decay persistence --------------------------------------

    def record_access(self, mem_id: str) -> None:
        self._decay.record_access(mem_id)

    def get_decay_score(self, mem_id: str) -> float:
        return self._decay.get_decay_score(mem_id)

    def apply_decay(self, decay_rate: float = 0.01) -> int:
        return self._decay.apply_decay(decay_rate)

    # --- WS-F W6: Search hardening ---------------------------------------

    def search_safe(
        self, query: str, kind: str | None = None, limit: int = 10
    ) -> list[Memory]:
        return self._search.search_safe(query, kind=kind, limit=limit)
