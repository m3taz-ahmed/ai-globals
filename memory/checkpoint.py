#!/usr/bin/env python3
"""Checkpoint-based durable state for aiZee agents.

Inspired by LangGraph's checkpointing model: each agent step produces a
``Checkpoint`` capturing per-channel state with monotonically increasing
channel versions. Checkpoints form a parent-child chain so the full history
of an agent run can be replayed or rolled back.

Channel reducers (``append_reducer``, ``last_value_reducer``,
``subtract_reducer``) define how a channel's value is updated when a new
value is written — mirroring LangGraph's ``Annotated`` reducer pattern.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Any, TypedDict

# ---------------------------------------------------------------------------
# Channel reducers
# ---------------------------------------------------------------------------

def append_reducer(existing: list[Any] | None, new: list[Any] | None) -> list[Any]:
    """Append ``new`` items to ``existing`` list (additive channel)."""
    return (existing or []) + (new or [])


def last_value_reducer(existing: Any, new: Any) -> Any:
    """Replace ``existing`` with ``new`` (default overwrite semantics)."""
    return new


def subtract_reducer(existing: float | None, new: float) -> float:
    """Subtract ``new`` from ``existing`` (budget-decrement channel)."""
    return (existing or 0.0) - new


# ---------------------------------------------------------------------------
# Agent state (TypedDict with Annotated reducers)
# ---------------------------------------------------------------------------

class AizeeAgentState(TypedDict):
    """Example agent state showing how channel reducers compose.

    ``messages`` and ``audit_log`` are append-only channels.
    ``current_persona`` uses implicit last-value semantics.
    ``budget_remaining`` is decremented via ``subtract_reducer``.
    """

    messages: Annotated[list[Any], append_reducer]
    current_persona: str  # implicit last_value
    budget_remaining: Annotated[float, subtract_reducer]
    audit_log: Annotated[list[Any], append_reducer]
    policy_decisions: Annotated[list[Any], append_reducer]


# ---------------------------------------------------------------------------
# Checkpoint data model
# ---------------------------------------------------------------------------

@dataclass
class Checkpoint:
    """A single durable snapshot of agent state.

    Attributes:
        checkpoint_id: Unique identifier (UUID) for this checkpoint.
        parent_id: Parent checkpoint id for history chaining (None for root).
        created_at: Unix timestamp of creation.
        channel_values: Per-channel state values.
        channel_versions: Monotonically increasing version per channel.
        metadata: Arbitrary metadata (step, source, tags, etc.).
    """

    checkpoint_id: str
    parent_id: str | None
    created_at: float
    channel_values: dict[str, Any]
    channel_versions: dict[str, int]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize this checkpoint to a plain dict."""
        return {
            "checkpoint_id": self.checkpoint_id,
            "parent_id": self.parent_id,
            "created_at": self.created_at,
            "channel_values": self.channel_values,
            "channel_versions": self.channel_versions,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Checkpoint:
        """Reconstruct a checkpoint from a plain dict."""
        if not isinstance(data, dict):
            raise ValueError("Checkpoint data must be a mapping")
        values = data.get("channel_values", {})
        versions = data.get("channel_versions", {})
        meta = data.get("metadata", {})
        if not isinstance(values, dict) or not isinstance(versions, dict) or not isinstance(meta, dict):
            raise ValueError("Checkpoint channel_values/channel_versions/metadata must be mappings")
        return cls(
            checkpoint_id=data["checkpoint_id"],
            parent_id=data.get("parent_id"),
            created_at=data["created_at"],
            channel_values=values,
            channel_versions=versions,
            metadata=meta,
        )


def create_checkpoint(
    parent: Checkpoint | None = None,
    channel_values: dict[str, Any] | None = None,
    channel_versions: dict[str, int] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Checkpoint:
    """Build a new checkpoint linked to an optional parent.

    Versions are always derived from the parent (monotonic bump per
    channel present in ``channel_values``). A caller-supplied
    ``channel_versions`` is honored only for root checkpoints (no parent),
    where there is nothing to inherit — otherwise it is ignored so stale
    versions can never override the computed chain.
    """
    parent_versions = dict(parent.channel_versions) if parent else {}
    new_versions = dict(parent_versions)
    values = channel_values or {}
    for ch in values:
        new_versions[ch] = parent_versions.get(ch, 0) + 1
    if parent is None and channel_versions:
        new_versions.update(channel_versions)
    return Checkpoint(
        checkpoint_id=str(uuid.uuid4()),
        parent_id=parent.checkpoint_id if parent else None,
        created_at=time.time(),
        channel_values=values,
        channel_versions=new_versions,
        metadata=metadata or {},
    )


# ---------------------------------------------------------------------------
# Base checkpoint saver
# ---------------------------------------------------------------------------

class BaseCheckpointSaver(ABC):
    """Abstract base for checkpoint persistence backends."""

    @abstractmethod
    def put(self, config: dict[str, Any], checkpoint: Checkpoint, metadata: dict[str, Any]) -> None:
        """Persist a checkpoint under the given config (thread/run identifier)."""
        ...

    @abstractmethod
    def get(self, config: dict[str, Any]) -> Checkpoint | None:
        """Retrieve the latest checkpoint for a config, or None."""
        ...

    @abstractmethod
    def list(self, config: dict[str, Any], limit: int = 10) -> list[Checkpoint]:
        """Return the checkpoint history for a config (newest first)."""
        ...


# ---------------------------------------------------------------------------
# SQLite checkpoint saver
# ---------------------------------------------------------------------------

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS checkpoints (
    id TEXT PRIMARY KEY,
    parent_id TEXT,
    created_at REAL,
    channel_values TEXT,
    channel_versions TEXT,
    metadata TEXT,
    thread_id TEXT
)
"""

_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_checkpoints_parent ON checkpoints(parent_id)
"""

_THREAD_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_checkpoints_thread ON checkpoints(thread_id, created_at DESC)
"""


class SqliteCheckpointSaver(BaseCheckpointSaver):
    """SQLite-backed checkpoint saver.

    A single ``checkpoints`` table stores every checkpoint. The ``config``
    dict must contain a ``thread_id`` key identifying the agent run; an
    optional ``checkpoint_id`` narrows ``get`` to a specific checkpoint.
    """

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        # Single shared connection with check_same_thread=False requires
        # explicit serialization of access across threads. A connection pool
        # is intentionally NOT used here because checkpoint save/load is
        # strictly serial (one writer, WAL mode, RLock-guarded) — a pool
        # would add complexity without benefit for this access pattern.
        self._lock = threading.RLock()
        self._closed = False
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(_SCHEMA_SQL)
        self._conn.execute(_INDEX_SQL)
        # Migrate pre-existing DBs: backfill the thread_id column + index.
        cols = {row[1] for row in self._conn.execute("PRAGMA table_info(checkpoints)").fetchall()}
        if "thread_id" not in cols:
            self._conn.execute("ALTER TABLE checkpoints ADD COLUMN thread_id TEXT")
            self._conn.execute(
                "UPDATE checkpoints SET thread_id = CAST(json_extract(metadata, '$.thread_id') AS TEXT)"
            )
        self._conn.execute(_THREAD_INDEX_SQL)
        self._conn.commit()

    def _ensure_open(self) -> None:
        if self._closed:
            raise ValueError("SqliteCheckpointSaver is closed")

    def _config_thread(self, config: dict[str, Any]) -> str:
        thread_id = config.get("thread_id")
        if not thread_id:
            raise ValueError("config must contain a non-empty 'thread_id'")
        return str(thread_id)

    def put(self, config: dict[str, Any], checkpoint: Checkpoint, metadata: dict[str, Any]) -> None:
        """Insert a new checkpoint. Metadata is merged into the checkpoint."""
        # config thread_id is stored in metadata for traceability.
        merged_meta = {**checkpoint.metadata, **metadata, "thread_id": self._config_thread(config)}
        self._ensure_open()
        with self._lock:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO checkpoints
                    (id, parent_id, created_at, channel_values, channel_versions, metadata, thread_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    checkpoint.checkpoint_id,
                    checkpoint.parent_id,
                    checkpoint.created_at,
                    json.dumps(checkpoint.channel_values, default=str),
                    json.dumps(checkpoint.channel_versions, default=str),
                    json.dumps(merged_meta, default=str),
                    self._config_thread(config),
                ),
            )
            self._conn.commit()

    def get(self, config: dict[str, Any]) -> Checkpoint | None:
        """Retrieve the latest checkpoint for a config.

        If ``config`` contains a ``checkpoint_id``, that specific checkpoint
        is returned; otherwise the most recent one for the thread is returned.
        """
        thread_id = self._config_thread(config)
        specific = config.get("checkpoint_id")
        self._ensure_open()
        with self._lock:
            if specific:
                row = self._conn.execute(
                    "SELECT * FROM checkpoints WHERE id = ?",
                    (specific,),
                ).fetchone()
            else:
                row = self._conn.execute(
                    """
                    SELECT * FROM checkpoints
                    WHERE thread_id = ?
                    ORDER BY created_at DESC, rowid DESC
                    LIMIT 1
                    """,
                    (thread_id,),
                ).fetchone()
        return self._row_to_checkpoint(row) if row else None

    def list(self, config: dict[str, Any], limit: int = 10) -> list[Checkpoint]:
        """Return checkpoint history for a config, newest first."""
        thread_id = self._config_thread(config)
        try:
            limit = max(1, min(int(limit), 500))
        except (TypeError, ValueError):
            limit = 10
        self._ensure_open()
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT * FROM checkpoints
                WHERE thread_id = ?
                ORDER BY created_at DESC, rowid DESC
                LIMIT ?
                """,
                (thread_id, limit),
            ).fetchall()
        return [self._row_to_checkpoint(row) for row in rows]

    @staticmethod
    def _row_to_checkpoint(row: sqlite3.Row) -> Checkpoint:
        try:
            return Checkpoint(
                checkpoint_id=row["id"],
                parent_id=row["parent_id"],
                created_at=row["created_at"],
                channel_values=json.loads(row["channel_values"] or "{}"),
                channel_versions=json.loads(row["channel_versions"] or "{}"),
                metadata=json.loads(row["metadata"] or "{}"),
            )
        except (ValueError, KeyError, TypeError) as exc:
            raise ValueError(f"Corrupt checkpoint row {row['id']!r}: {exc}") from exc

    def close(self) -> None:
        """Close the underlying SQLite connection (idempotent)."""
        with self._lock:
            if not self._closed:
                self._closed = True
                self._conn.close()
