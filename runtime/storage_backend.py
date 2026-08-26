"""Pluggable storage backend abstraction for aiZee.

Inspired by Floci's ``StorageBackend<K,V>`` interface + ``StorageFactory``
pattern. Provides a uniform interface for key-value stores with multiple
implementations (in-memory, JSON-file, SQLite) selected by configuration.

The abstraction is additive — existing ``MemoryStore`` (SQLite) is NOT
modified. New code can opt into the abstraction; legacy code keeps working.

Usage::

    from runtime.storage_backend import StorageFactory, StorageMode

    factory = StorageFactory()
    backend = factory.create("rules", "rules.json", dict)
    backend.put("git-01", {"condition": "type == 'Read'", "action": "allow"})
    rule = backend.get("git-01")  # → {"condition": ..., "action": ...}
    factory.shutdown_all()
"""

from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Protocol, TypeVar, runtime_checkable

K = TypeVar("K")
V = TypeVar("V")


class StorageMode(str, Enum):
    """Available storage backend modes."""

    MEMORY = "memory"
    JSON = "json"
    SQLITE = "sqlite"


@runtime_checkable
class StorageBackend(Protocol[K, V]):
    """Generic key-value storage backend protocol.

    All implementations must provide these operations.
    Inspired by Floci's ``StorageBackend<K,V>`` interface.
    """

    def put(self, key: K, value: V) -> None: ...
    def get(self, key: K) -> V | None: ...
    def delete(self, key: K) -> bool: ...
    def scan(self, key_filter: Any | None = None) -> list[V]: ...
    def keys(self) -> list[K]: ...
    def flush(self) -> None: ...
    def load(self) -> None: ...
    def clear(self) -> None: ...
    def count(self) -> int: ...


class InMemoryStorage(StorageBackend[Any, Any]):
    """In-memory dict-backed storage. Lost on process exit."""

    def __init__(self) -> None:
        self._data: dict[Any, Any] = {}
        self._lock = threading.Lock()

    def put(self, key: Any, value: Any) -> None:
        with self._lock:
            self._data[key] = value

    def get(self, key: Any) -> Any | None:
        with self._lock:
            return self._data.get(key)

    def delete(self, key: Any) -> bool:
        with self._lock:
            if key in self._data:
                del self._data[key]
                return True
            return False

    def scan(self, key_filter: Any | None = None) -> list[Any]:
        with self._lock:
            if key_filter is None:
                return list(self._data.values())
            if callable(key_filter):
                return [v for k, v in self._data.items() if key_filter(k)]
            return [v for k, v in self._data.items() if k == key_filter]

    def keys(self) -> list[Any]:
        with self._lock:
            return list(self._data.keys())

    def flush(self) -> None:
        """No-op for in-memory storage."""

    def load(self) -> None:
        """No-op for in-memory storage."""

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def count(self) -> int:
        with self._lock:
            return len(self._data)


class JsonFileStorage(StorageBackend[Any, Any]):
    """JSON-file-backed persistent storage. Loads/saves entire dict on each flush."""

    def __init__(self, file_path: Path) -> None:
        self._path = file_path
        self._data: dict[Any, Any] = {}
        self._lock = threading.Lock()
        self._loaded = False

    def load(self) -> None:
        if self._loaded:
            return
        with self._lock:
            if self._path.exists():
                try:
                    raw = json.loads(self._path.read_text(encoding="utf-8"))
                    if isinstance(raw, dict):
                        # JSON keys are always strings; keep as-is
                        self._data = raw
                except (json.JSONDecodeError, OSError):
                    self._data = {}
            self._loaded = True

    def put(self, key: Any, value: Any) -> None:
        with self._lock:
            self._data[str(key)] = value

    def get(self, key: Any) -> Any | None:
        with self._lock:
            return self._data.get(str(key))

    def delete(self, key: Any) -> bool:
        with self._lock:
            str_key = str(key)
            if str_key in self._data:
                del self._data[str_key]
                return True
            return False

    def scan(self, key_filter: Any | None = None) -> list[Any]:
        with self._lock:
            if key_filter is None:
                return list(self._data.values())
            if callable(key_filter):
                return [v for k, v in self._data.items() if key_filter(k)]
            return [v for k, v in self._data.items() if k == str(key_filter)]

    def keys(self) -> list[Any]:
        with self._lock:
            return list(self._data.keys())

    def flush(self) -> None:
        with self._lock:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(self._data, indent=2, default=str), encoding="utf-8",
            )

    def clear(self) -> None:
        with self._lock:
            self._data.clear()
        self.flush()

    def count(self) -> int:
        with self._lock:
            return len(self._data)


class SqliteStorage(StorageBackend[Any, Any]):
    """SQLite-backed persistent storage with automatic table creation.

    Uses JSON serialization for values. Keys are stored as TEXT.
    Suitable for larger datasets than JsonFileStorage.
    """

    def __init__(self, db_path: Path, table_name: str = "kv_store") -> None:
        self._db_path = db_path
        self._table = table_name
        self._lock = threading.Lock()
        self._conn: sqlite3.Connection | None = None

    def _connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(
                str(self._db_path),
                check_same_thread=False,
                isolation_level=None,  # autocommit
            )
            self._conn.execute(
                f"CREATE TABLE IF NOT EXISTS {self._table} "
                f"(key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            self._conn.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{self._table}_key ON {self._table}(key)"
            )
        return self._conn

    def load(self) -> None:
        """SQLite loads lazily on first access — no bulk load needed."""
        self._connect()

    def put(self, key: Any, value: Any) -> None:
        conn = self._connect()
        with self._lock:
            conn.execute(
                f"INSERT OR REPLACE INTO {self._table} (key, value) VALUES (?, ?)",
                (str(key), json.dumps(value, default=str)),
            )

    def get(self, key: Any) -> Any | None:
        conn = self._connect()
        with self._lock:
            row = conn.execute(
                f"SELECT value FROM {self._table} WHERE key = ?", (str(key),)
            ).fetchone()
        if row is None:
            return None
        try:
            return json.loads(row[0])
        except json.JSONDecodeError:
            return row[0]

    def delete(self, key: Any) -> bool:
        conn = self._connect()
        with self._lock:
            cursor = conn.execute(
                f"DELETE FROM {self._table} WHERE key = ?", (str(key),)
            )
            return cursor.rowcount > 0

    def scan(self, key_filter: Any | None = None) -> list[Any]:
        conn = self._connect()
        with self._lock:
            if key_filter is None:
                rows = conn.execute(
                    f"SELECT value FROM {self._table}"
                ).fetchall()
            elif callable(key_filter):
                # Fetch all then filter in Python (key_filter is a predicate)
                rows = conn.execute(
                    f"SELECT key, value FROM {self._table}"
                ).fetchall()
                return [
                    json.loads(r[1])
                    for r in rows
                    if key_filter(r[0])
                ]
            else:
                rows = conn.execute(
                    f"SELECT value FROM {self._table} WHERE key = ?",
                    (str(key_filter),),
                ).fetchall()
        return [json.loads(r[0]) for r in rows]

    def keys(self) -> list[Any]:
        conn = self._connect()
        with self._lock:
            rows = conn.execute(
                f"SELECT key FROM {self._table}"
            ).fetchall()
        return [r[0] for r in rows]

    def flush(self) -> None:
        """SQLite autocommit mode — no explicit flush needed."""

    def clear(self) -> None:
        conn = self._connect()
        with self._lock:
            conn.execute(f"DELETE FROM {self._table}")

    def count(self) -> int:
        conn = self._connect()
        with self._lock:
            row = conn.execute(
                f"SELECT COUNT(*) FROM {self._table}"
            ).fetchone()
        return int(row[0]) if row else 0

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None


@dataclass
class _TrackedBackend:
    """Internal tracking entry for a created backend."""

    backend: Any
    mode: StorageMode
    path: Path | None = None


class StorageFactory:
    """Factory that creates and tracks storage backends by configuration.

    Inspired by Floci's ``StorageFactory``. Centralizes backend lifecycle:
    create → load → use → flush → shutdown.

    Backends are cached by path — repeat ``create()`` with the same path
    returns the existing backend (prevents duplicate stores clobbering
    persisted state on shutdown, mirroring Floci issue #1921).
    """

    def __init__(self, base_dir: Path | None = None, default_mode: StorageMode = StorageMode.MEMORY) -> None:
        self._base_dir = base_dir or Path(".aizee/storage")
        self._default_mode = default_mode
        self._backends: list[_TrackedBackend] = []
        self._by_path: dict[Path, _TrackedBackend] = {}
        self._lock = threading.Lock()

    def create(
        self,
        name: str,
        file_name: str | None = None,
        mode: StorageMode | None = None,
    ) -> Any:
        """Create or reuse a storage backend.

        Args:
            name: Logical name for the backend (used in logging/debugging).
            file_name: File name for persistent modes (json/sqlite).
                       If None, only memory mode is valid.
            mode: Storage mode. Defaults to factory's default_mode.

        Returns:
            A StorageBackend implementation instance.
        """
        effective_mode = mode or self._default_mode
        if effective_mode == StorageMode.MEMORY and file_name is None:
            backend: Any = InMemoryStorage()
            with self._lock:
                self._backends.append(_TrackedBackend(backend, effective_mode))
            return backend

        if file_name is None:
            raise ValueError(f"file_name required for {effective_mode.value} mode")

        file_path = self._base_dir / file_name
        with self._lock:
            existing = self._by_path.get(file_path)
            if existing is not None:
                return existing.backend

        if effective_mode == StorageMode.JSON:
            backend = JsonFileStorage(file_path)
        elif effective_mode == StorageMode.SQLITE:
            db_path = file_path if file_path.suffix == ".db" else file_path.with_suffix(".db")
            backend = SqliteStorage(db_path, table_name=name.replace("-", "_"))
        else:
            raise ValueError(f"Unknown storage mode: {effective_mode}")

        backend.load()
        with self._lock:
            tracked = _TrackedBackend(backend, effective_mode, file_path)
            self._backends.append(tracked)
            self._by_path[file_path] = tracked
        return backend

    def load_all(self) -> None:
        """Load all tracked backends from disk."""
        with self._lock:
            backends = list(self._backends)
        for tracked in backends:
            tracked.backend.load()

    def flush_all(self) -> None:
        """Flush all tracked backends to disk."""
        with self._lock:
            backends = list(self._backends)
        for tracked in backends:
            tracked.backend.flush()

    def clear_all(self) -> None:
        """Clear all tracked backends and flush."""
        with self._lock:
            backends = list(self._backends)
        for tracked in backends:
            tracked.backend.clear()
        self.flush_all()

    def shutdown_all(self) -> None:
        """Shutdown all tracked backends (flush + close connections)."""
        with self._lock:
            backends = list(self._backends)
        for tracked in backends:
            tracked.backend.flush()
            if isinstance(tracked.backend, SqliteStorage):
                tracked.backend.close()
        with self._lock:
            self._backends.clear()
            self._by_path.clear()

    def count(self) -> int:
        """Return number of tracked backends."""
        with self._lock:
            return len(self._backends)

    def modes_in_use(self) -> list[StorageMode]:
        """Return distinct modes currently in use."""
        with self._lock:
            return list({t.mode for t in self._backends})


# Module-level default factory (lazy-initialized for test isolation)
_default_factory: StorageFactory | None = None


def get_default_factory() -> StorageFactory:
    """Get or create the module-level default StorageFactory."""
    global _default_factory
    if _default_factory is None:
        _default_factory = StorageFactory()
    return _default_factory


class MemoryStoreAdapter(StorageBackend[str, Any]):
    """Bridge adapter: wraps ``MemoryStore`` to implement ``StorageBackend`` protocol.

    This allows new code using ``StorageFactory`` to access the rich
    ``MemoryStore`` (SQLite + FTS5 + vector) through the uniform
    ``StorageBackend`` interface. Keys are memory IDs (str), values are
    ``Memory`` objects or dicts.

    The adapter delegates to ``MemoryStore.add_batch()`` for puts,
    ``MemoryStore.get()`` for lookups, and ``MemoryStore.invalidate()``
    for soft deletes. FTS5 search is available via the underlying store.
    """

    def __init__(self, store: Any) -> None:
        """Initialize with an existing ``MemoryStore`` instance."""
        self._store = store

    def put(self, key: str, value: Any) -> None:
        """Store a value under the given key (memory ID).

        If value is a ``Memory`` instance, inserts it directly.
        If value is a dict, constructs a ``Memory`` from dict fields.
        """
        from memory.store import Memory

        if isinstance(value, Memory):
            value.id = key
            self._store.add_batch([value])
        elif isinstance(value, dict):
            mem = Memory(
                id=key,
                kind=value.get("kind", "generic"),
                content=value.get("content", ""),
                source=value.get("source", ""),
                meta=value.get("meta", "{}"),
                created_at=value.get("created_at", ""),
                valid_from=value.get("valid_from", ""),
                valid_to=value.get("valid_to"),
            )
            self._store.add_batch([mem])
        else:
            # Fallback: stringify the value and store as content.
            mem = self._store.add("generic", str(value))
            # Override the generated ID with the provided key via direct update.
            with self._store._conn() as conn:
                conn.execute(
                    "UPDATE memories SET id = ? WHERE id = ?", (key, mem.id)
                )

    def get(self, key: str) -> Any:
        """Retrieve a memory by ID. Returns ``Memory`` or ``None``."""
        return self._store.get(key)

    def delete(self, key: str) -> bool:
        """Soft-delete a memory by ID (sets valid_to). Returns True if existed."""
        mem = self._store.get(key)
        if mem is None:
            return False
        self._store.invalidate(key)
        return True

    def scan(self, key_filter: Any | None = None) -> list[Any]:
        """List all memories, optionally filtered by kind (if key_filter is a str)."""
        kind = key_filter if isinstance(key_filter, str) else None
        return list(self._store.list_all(kind=kind))

    def keys(self) -> list[str]:
        """Return all memory IDs."""
        return [m.id for m in self._store.list_all(limit=100000)]

    def flush(self) -> None:
        """No-op — SQLite auto-persists on each write."""
        return None

    def load(self) -> None:
        """No-op — SQLite loads on connection."""
        return None

    def clear(self) -> None:
        """Delete all memories (hard delete)."""
        ids = self.keys()
        for mid in ids:
            self._store.delete_hard(mid)

    def count(self) -> int:
        """Return total memory count."""
        return int(self._store.count())

    @property
    def store(self) -> Any:
        """Access the underlying ``MemoryStore`` for advanced operations (FTS5, vector)."""
        return self._store
