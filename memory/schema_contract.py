#!/usr/bin/env python3
"""Contract-first schema verification with hash-based integrity checks.

Inspired by Prisma's declarative schema model: a ``SchemaContract`` captures
the expected DDL (tables + indexes) for a database. The contract is hashed
(SHA-256) so that any drift between the expected schema and the actual
database schema can be detected and reported precisely.

This module is purely additive — callers (e.g. ``MemoryStore``) use it to
*warn* about drift without blocking initialization.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class SchemaDrift:
    """A single detected difference between expected and actual schema.

    Attributes:
        drift_type: One of ``missing_table``, ``extra_table``,
            ``column_mismatch``, ``index_missing``.
        table_name: Name of the affected table (or index name for index drift).
        expected: Expected DDL fragment (empty string when N/A).
        actual: Actual DDL fragment (empty string when N/A).
    """

    drift_type: str
    table_name: str
    expected: str
    actual: str


@dataclass
class SchemaContract:
    """Declarative schema contract with content hashing.

    Attributes:
        tables: Mapping of table name -> CREATE TABLE DDL.
        indexes: Mapping of index name -> CREATE INDEX DDL.
        version: Schema version label (e.g. ``"v2"``).
        content_hash: SHA-256 of the serialized contract (excluding the hash
            itself). Recomputed via :meth:`compute_hash`.
    """

    tables: dict[str, str] = field(default_factory=dict)
    indexes: dict[str, str] = field(default_factory=dict)
    version: str = ""
    content_hash: str = ""

    # ------------------------------------------------------------------
    # Hashing & serialization
    # ------------------------------------------------------------------

    def _payload(self) -> dict[str, Any]:
        """Return the canonical dict that gets hashed (excludes content_hash)."""
        return {
            "tables": dict(sorted(self.tables.items())),
            "indexes": dict(sorted(self.indexes.items())),
            "version": self.version,
        }

    def compute_hash(self) -> str:
        """Compute the SHA-256 hash of the contract content."""
        payload = json.dumps(self._payload(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def serialize(self) -> str:
        """Serialize the contract (including its hash) to a JSON string."""
        self.content_hash = self.compute_hash()
        return json.dumps(
            {**self._payload(), "content_hash": self.content_hash},
            sort_keys=True,
            indent=2,
        )

    @classmethod
    def deserialize(cls, json_str: str) -> SchemaContract:
        """Reconstruct a :class:`SchemaContract` from a JSON string."""
        data = json.loads(json_str)
        contract = cls(
            tables=data.get("tables", {}),
            indexes=data.get("indexes", {}),
            version=data.get("version", ""),
        )
        contract.content_hash = data.get("content_hash", contract.compute_hash())
        return contract

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def apply(self, conn: sqlite3.Connection) -> None:
        """Apply all DDL statements in this contract to a connection."""
        for ddl in self.tables.values():
            conn.execute(ddl)
        for ddl in self.indexes.values():
            conn.execute(ddl)


# ---------------------------------------------------------------------------
# SQL normalization
# ---------------------------------------------------------------------------

_WS_RE = re.compile(r"\s+")
_IF_NOT_EXISTS_RE = re.compile(r"\bif\s+not\s+exists\b", re.IGNORECASE)


def _normalize_sql(sql: str) -> str:
    """Collapse whitespace, drop ``IF NOT EXISTS``, and lowercase for comparison.

    SQLite strips ``IF NOT EXISTS`` from the DDL it stores in ``sqlite_master``,
    so the expected contract DDL must be normalized the same way to compare.
    """
    if not sql:
        return ""
    no_ifne = _IF_NOT_EXISTS_RE.sub("", sql)
    return _WS_RE.sub(" ", no_ifne).strip().lower()


# ---------------------------------------------------------------------------
# DB introspection
# ---------------------------------------------------------------------------

def _read_db_schema(db_path: Path) -> tuple[dict[str, str], dict[str, str]]:
    """Read the actual table and index DDL from a SQLite database.

    Returns ``(tables, indexes)`` mappings of name -> raw SQL.
    Auto-indexes (those with NULL sql, e.g. from UNIQUE constraints) are
    excluded from the index map.
    """
    tables: dict[str, str] = {}
    indexes: dict[str, str] = {}
    if not db_path.exists():
        return tables, indexes
    with sqlite3.connect(db_path) as conn:
        for row in conn.execute("SELECT name, sql FROM sqlite_master WHERE type='table'"):
            name, sql = row
            if name.startswith("sqlite_"):
                continue
            tables[name] = sql or ""
        for row in conn.execute("SELECT name, sql FROM sqlite_master WHERE type='index'"):
            name, sql = row
            if not sql:  # skip auto-indexes
                continue
            indexes[name] = sql
    return tables, indexes


# ---------------------------------------------------------------------------
# Drift detection
# ---------------------------------------------------------------------------

def detect_schema_drift(
    db_path: Path, expected: SchemaContract | None = None
) -> list[SchemaDrift]:
    """Return a list of specific drift items between expected and actual schema.

    If ``expected`` is None, the default memory-store contract is used.
    """
    if expected is None:
        expected = default_memory_contract()
    actual_tables, actual_indexes = _read_db_schema(db_path)
    drifts: list[SchemaDrift] = []

    # Missing / mismatched tables
    for tname, expected_ddl in expected.tables.items():
        if tname not in actual_tables:
            drifts.append(SchemaDrift("missing_table", tname, expected_ddl, ""))
        elif _normalize_sql(actual_tables[tname]) != _normalize_sql(expected_ddl):
            drifts.append(
                SchemaDrift("column_mismatch", tname, expected_ddl, actual_tables[tname])
            )

    # Extra tables — ignore FTS5 shadow tables (memories_fts, memories_fts_data,
    # memories_fts_idx, memories_fts_docsize, memories_fts_config) which SQLite
    # creates automatically alongside the virtual table and are not part of the
    # contract. Also ignore sqlite_* internal tables (already filtered in _read_db_schema).
    for tname, actual_ddl in actual_tables.items():
        if tname not in expected.tables and not tname.startswith("memories_fts"):
            drifts.append(SchemaDrift("extra_table", tname, "", actual_ddl))

    # Missing indexes
    for iname, expected_ddl in expected.indexes.items():
        if iname not in actual_indexes:
            drifts.append(SchemaDrift("index_missing", iname, expected_ddl, ""))
        elif _normalize_sql(actual_indexes[iname]) != _normalize_sql(expected_ddl):
            drifts.append(
                SchemaDrift("index_missing", iname, expected_ddl, actual_indexes[iname])
            )

    return drifts


def verify_schema_integrity(
    db_path: Path, expected: SchemaContract | None = None
) -> tuple[bool, str | None]:
    """Verify that the actual DB schema matches the expected contract hash.

    Returns ``(is_valid, drift_description)``. When valid, the description is
    ``None``. When invalid, a human-readable summary of the drift is returned.
    """
    if expected is None:
        expected = default_memory_contract()
    actual_tables, actual_indexes = _read_db_schema(db_path)
    actual_contract = SchemaContract(
        tables=actual_tables,
        indexes=actual_indexes,
        version=expected.version,
    )
    actual_hash = actual_contract.compute_hash()
    if actual_hash == expected.content_hash or actual_hash == expected.compute_hash():
        return (True, None)
    # SQLite reformats DDL (e.g. strips IF NOT EXISTS, normalizes whitespace),
    # so hashes may differ even when schemas are structurally identical.
    # Fall back to structural drift detection — if no drift, consider it valid.
    drifts = detect_schema_drift(db_path, expected)
    if not drifts:
        return (True, None)
    parts = [f"{d.drift_type}:{d.table_name}" for d in drifts]
    return (False, "; ".join(parts))


# ---------------------------------------------------------------------------
# Default memory-store contract
# ---------------------------------------------------------------------------

def default_memory_contract() -> SchemaContract:
    """Build the canonical :class:`SchemaContract` for the aiZee memory store."""
    tables: dict[str, str] = {
        "memories": """
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
        "relations": """
            CREATE TABLE IF NOT EXISTS relations (
                id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relation TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """,
        "memory_decay": """
            CREATE TABLE IF NOT EXISTS memory_decay (
                mem_id TEXT PRIMARY KEY,
                decay_score REAL NOT NULL DEFAULT 1.0,
                last_accessed TEXT NOT NULL,
                access_count INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (mem_id) REFERENCES memories(id)
            )
        """,
    }
    indexes: dict[str, str] = {
        "idx_mem_kind": "CREATE INDEX IF NOT EXISTS idx_mem_kind ON memories(kind)",
        "idx_mem_source": "CREATE INDEX IF NOT EXISTS idx_mem_source ON memories(source)",
        "idx_mem_valid_to": "CREATE INDEX IF NOT EXISTS idx_mem_valid_to ON memories(valid_to)",
        "idx_rel_source": "CREATE INDEX IF NOT EXISTS idx_rel_source ON relations(source_id)",
        "idx_rel_target": "CREATE INDEX IF NOT EXISTS idx_rel_target ON relations(target_id)",
        "idx_decay_last_accessed": "CREATE INDEX IF NOT EXISTS idx_decay_last_accessed ON memory_decay(last_accessed)",
    }
    contract = SchemaContract(tables=tables, indexes=indexes, version="v2")
    contract.content_hash = contract.compute_hash()
    return contract
