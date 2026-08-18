"""Tests for runtime/storage_backend.py — pluggable storage abstraction.

Covers: InMemoryStorage, JsonFileStorage, SqliteStorage, StorageFactory.
FAST tier — no MCP, no kernel, no model loading.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from runtime.storage_backend import (
    InMemoryStorage,
    JsonFileStorage,
    MemoryStoreAdapter,
    SqliteStorage,
    StorageBackend,
    StorageFactory,
    StorageMode,
)

# -- InMemoryStorage -------------------------------------------------------


class TestInMemoryStorage:
    def test_put_and_get(self) -> None:
        store = InMemoryStorage()
        store.put("key1", "value1")
        assert store.get("key1") == "value1"

    def test_get_missing_returns_none(self) -> None:
        store = InMemoryStorage()
        assert store.get("nonexistent") is None

    def test_delete_existing(self) -> None:
        store = InMemoryStorage()
        store.put("key1", "value1")
        assert store.delete("key1") is True
        assert store.get("key1") is None

    def test_delete_missing_returns_false(self) -> None:
        store = InMemoryStorage()
        assert store.delete("nonexistent") is False

    def test_keys(self) -> None:
        store = InMemoryStorage()
        store.put("a", 1)
        store.put("b", 2)
        assert set(store.keys()) == {"a", "b"}

    def test_scan_all(self) -> None:
        store = InMemoryStorage()
        store.put("a", 1)
        store.put("b", 2)
        assert set(store.scan()) == {1, 2}

    def test_scan_with_predicate(self) -> None:
        store = InMemoryStorage()
        store.put("a", 1)
        store.put("b", 2)
        store.put("c", 3)
        result = store.scan(lambda k: k in ("a", "c"))
        assert set(result) == {1, 3}

    def test_clear(self) -> None:
        store = InMemoryStorage()
        store.put("a", 1)
        store.clear()
        assert store.count() == 0

    def test_count(self) -> None:
        store = InMemoryStorage()
        assert store.count() == 0
        store.put("a", 1)
        store.put("b", 2)
        assert store.count() == 2

    def test_flush_and_load_are_noops(self) -> None:
        store = InMemoryStorage()
        store.put("a", 1)
        store.flush()  # should not raise
        store.load()   # should not raise
        assert store.get("a") == 1

    def test_implements_protocol(self) -> None:
        store = InMemoryStorage()
        assert isinstance(store, StorageBackend)


# -- JsonFileStorage -------------------------------------------------------


class TestJsonFileStorage:
    def test_put_and_get(self, tmp_path: Path) -> None:
        store = JsonFileStorage(tmp_path / "test.json")
        store.load()
        store.put("key1", {"name": "test", "value": 42})
        assert store.get("key1") == {"name": "test", "value": 42}

    def test_persistence_across_instances(self, tmp_path: Path) -> None:
        file_path = tmp_path / "persist.json"
        store1 = JsonFileStorage(file_path)
        store1.load()
        store1.put("key1", "value1")
        store1.flush()

        store2 = JsonFileStorage(file_path)
        store2.load()
        assert store2.get("key1") == "value1"

    def test_delete(self, tmp_path: Path) -> None:
        store = JsonFileStorage(tmp_path / "test.json")
        store.load()
        store.put("key1", "value1")
        assert store.delete("key1") is True
        assert store.get("key1") is None

    def test_keys(self, tmp_path: Path) -> None:
        store = JsonFileStorage(tmp_path / "test.json")
        store.load()
        store.put("a", 1)
        store.put("b", 2)
        assert set(store.keys()) == {"a", "b"}

    def test_scan(self, tmp_path: Path) -> None:
        store = JsonFileStorage(tmp_path / "test.json")
        store.load()
        store.put("a", 1)
        store.put("b", 2)
        assert set(store.scan()) == {1, 2}

    def test_clear(self, tmp_path: Path) -> None:
        store = JsonFileStorage(tmp_path / "test.json")
        store.load()
        store.put("a", 1)
        store.clear()
        assert store.count() == 0

    def test_count(self, tmp_path: Path) -> None:
        store = JsonFileStorage(tmp_path / "test.json")
        store.load()
        assert store.count() == 0
        store.put("a", 1)
        assert store.count() == 1

    def test_load_missing_file(self, tmp_path: Path) -> None:
        """Loading a non-existent file should not raise."""
        store = JsonFileStorage(tmp_path / "nonexistent.json")
        store.load()
        assert store.count() == 0

    def test_load_corrupted_json(self, tmp_path: Path) -> None:
        """Corrupted JSON should result in empty store, not crash."""
        file_path = tmp_path / "corrupt.json"
        file_path.write_text("{invalid json", encoding="utf-8")
        store = JsonFileStorage(file_path)
        store.load()
        assert store.count() == 0


# -- SqliteStorage ---------------------------------------------------------


class TestSqliteStorage:
    def test_put_and_get(self, tmp_path: Path) -> None:
        store = SqliteStorage(tmp_path / "test.db")
        store.load()
        store.put("key1", {"name": "test", "value": 42})
        assert store.get("key1") == {"name": "test", "value": 42}

    def test_persistence_across_instances(self, tmp_path: Path) -> None:
        db_path = tmp_path / "persist.db"
        store1 = SqliteStorage(db_path)
        store1.load()
        store1.put("key1", "value1")
        store1.flush()
        store1.close()

        store2 = SqliteStorage(db_path)
        store2.load()
        assert store2.get("key1") == "value1"
        store2.close()

    def test_delete(self, tmp_path: Path) -> None:
        store = SqliteStorage(tmp_path / "test.db")
        store.load()
        store.put("key1", "value1")
        assert store.delete("key1") is True
        assert store.get("key1") is None

    def test_delete_missing(self, tmp_path: Path) -> None:
        store = SqliteStorage(tmp_path / "test.db")
        store.load()
        assert store.delete("nonexistent") is False

    def test_keys(self, tmp_path: Path) -> None:
        store = SqliteStorage(tmp_path / "test.db")
        store.load()
        store.put("a", 1)
        store.put("b", 2)
        assert set(store.keys()) == {"a", "b"}

    def test_scan_all(self, tmp_path: Path) -> None:
        store = SqliteStorage(tmp_path / "test.db")
        store.load()
        store.put("a", 1)
        store.put("b", 2)
        assert set(store.scan()) == {1, 2}

    def test_scan_with_predicate(self, tmp_path: Path) -> None:
        store = SqliteStorage(tmp_path / "test.db")
        store.load()
        store.put("a", 1)
        store.put("b", 2)
        store.put("c", 3)
        result = store.scan(lambda k: k in ("a", "c"))
        assert set(result) == {1, 3}

    def test_clear(self, tmp_path: Path) -> None:
        store = SqliteStorage(tmp_path / "test.db")
        store.load()
        store.put("a", 1)
        store.clear()
        assert store.count() == 0

    def test_count(self, tmp_path: Path) -> None:
        store = SqliteStorage(tmp_path / "test.db")
        store.load()
        assert store.count() == 0
        store.put("a", 1)
        store.put("b", 2)
        assert store.count() == 2

    def test_close_and_reconnect(self, tmp_path: Path) -> None:
        store = SqliteStorage(tmp_path / "test.db")
        store.load()
        store.put("a", 1)
        store.close()
        # Reconnect via load
        store.load()
        assert store.get("a") == 1
        store.close()


# -- StorageFactory --------------------------------------------------------


class TestStorageFactory:
    def test_create_memory_no_file(self, tmp_path: Path) -> None:
        factory = StorageFactory(base_dir=tmp_path, default_mode=StorageMode.MEMORY)
        backend = factory.create("test")
        assert isinstance(backend, InMemoryStorage)
        assert factory.count() == 1

    def test_create_json(self, tmp_path: Path) -> None:
        factory = StorageFactory(base_dir=tmp_path, default_mode=StorageMode.JSON)
        backend = factory.create("rules", "rules.json")
        assert isinstance(backend, JsonFileStorage)
        backend.put("key1", "value1")
        backend.flush()
        assert (tmp_path / "rules.json").exists()

    def test_create_sqlite(self, tmp_path: Path) -> None:
        factory = StorageFactory(base_dir=tmp_path, default_mode=StorageMode.SQLITE)
        backend = factory.create("memory", "memory.json")
        assert isinstance(backend, SqliteStorage)
        backend.put("key1", "value1")
        assert backend.get("key1") == "value1"

    def test_create_reuses_same_path(self, tmp_path: Path) -> None:
        """Repeat create() with same file_name returns same backend instance."""
        factory = StorageFactory(base_dir=tmp_path, default_mode=StorageMode.JSON)
        backend1 = factory.create("rules", "rules.json")
        backend2 = factory.create("rules", "rules.json")
        assert backend1 is backend2
        assert factory.count() == 1

    def test_create_memory_with_different_names(self, tmp_path: Path) -> None:
        factory = StorageFactory(base_dir=tmp_path, default_mode=StorageMode.MEMORY)
        b1 = factory.create("store1")
        b2 = factory.create("store2")
        assert b1 is not b2
        assert factory.count() == 2

    def test_create_requires_file_name_for_persistent(self, tmp_path: Path) -> None:
        factory = StorageFactory(base_dir=tmp_path, default_mode=StorageMode.JSON)
        with pytest.raises(ValueError, match="file_name required"):
            factory.create("test", mode=StorageMode.JSON)

    def test_flush_all(self, tmp_path: Path) -> None:
        factory = StorageFactory(base_dir=tmp_path, default_mode=StorageMode.JSON)
        b1 = factory.create("rules", "rules.json")
        b2 = factory.create("config", "config.json")
        b1.put("k1", "v1")
        b2.put("k2", "v2")
        factory.flush_all()
        assert (tmp_path / "rules.json").exists()
        assert (tmp_path / "config.json").exists()

    def test_clear_all(self, tmp_path: Path) -> None:
        factory = StorageFactory(base_dir=tmp_path, default_mode=StorageMode.MEMORY)
        b1 = factory.create("store1")
        b2 = factory.create("store2")
        b1.put("k1", "v1")
        b2.put("k2", "v2")
        factory.clear_all()
        assert b1.count() == 0
        assert b2.count() == 0

    def test_shutdown_all(self, tmp_path: Path) -> None:
        factory = StorageFactory(base_dir=tmp_path, default_mode=StorageMode.SQLITE)
        backend = factory.create("memory", "memory.json")
        backend.put("k1", "v1")
        factory.shutdown_all()
        assert factory.count() == 0

    def test_modes_in_use(self, tmp_path: Path) -> None:
        factory = StorageFactory(base_dir=tmp_path, default_mode=StorageMode.MEMORY)
        factory.create("mem1")
        factory.create("json1", "j.json", mode=StorageMode.JSON)
        modes = factory.modes_in_use()
        assert StorageMode.MEMORY in modes
        assert StorageMode.JSON in modes

    def test_get_default_factory_singleton(self) -> None:
        from runtime.storage_backend import get_default_factory
        f1 = get_default_factory()
        f2 = get_default_factory()
        assert f1 is f2


# -- MemoryStoreAdapter (Bridge) -------------------------------------------


class TestMemoryStoreAdapter:
    """Tests for the MemoryStoreAdapter bridge between MemoryStore and StorageBackend."""

    def _make_adapter(self, tmp_path: Path) -> MemoryStoreAdapter:
        from memory.store import MemoryStore

        store = MemoryStore(root=tmp_path, enable_vector=False)
        return MemoryStoreAdapter(store)

    def test_put_and_get_dict(self, tmp_path: Path) -> None:
        adapter = self._make_adapter(tmp_path)
        adapter.put("mem-1", {"kind": "rule", "content": "test content", "source": "test"})
        result = adapter.get("mem-1")
        assert result is not None
        assert result.content == "test content"
        assert result.kind == "rule"

    def test_get_missing_returns_none(self, tmp_path: Path) -> None:
        adapter = self._make_adapter(tmp_path)
        assert adapter.get("nonexistent") is None

    def test_delete_existing(self, tmp_path: Path) -> None:
        adapter = self._make_adapter(tmp_path)
        adapter.put("mem-2", {"kind": "note", "content": "delete me"})
        assert adapter.delete("mem-2") is True
        # Soft delete — still retrievable but invalidated
        mem = adapter.get("mem-2")
        assert mem is not None
        assert mem.valid_to is not None

    def test_delete_missing_returns_false(self, tmp_path: Path) -> None:
        adapter = self._make_adapter(tmp_path)
        assert adapter.delete("nope") is False

    def test_count(self, tmp_path: Path) -> None:
        adapter = self._make_adapter(tmp_path)
        assert adapter.count() == 0
        adapter.put("a", {"kind": "x", "content": "1"})
        adapter.put("b", {"kind": "x", "content": "2"})
        assert adapter.count() == 2

    def test_keys(self, tmp_path: Path) -> None:
        adapter = self._make_adapter(tmp_path)
        adapter.put("key-a", {"kind": "x", "content": "1"})
        adapter.put("key-b", {"kind": "x", "content": "2"})
        keys = set(adapter.keys())
        assert "key-a" in keys
        assert "key-b" in keys

    def test_scan_all(self, tmp_path: Path) -> None:
        adapter = self._make_adapter(tmp_path)
        adapter.put("s1", {"kind": "rule", "content": "r1"})
        adapter.put("s2", {"kind": "note", "content": "n1"})
        all_items = adapter.scan()
        assert len(all_items) == 2

    def test_scan_filtered_by_kind(self, tmp_path: Path) -> None:
        adapter = self._make_adapter(tmp_path)
        adapter.put("s1", {"kind": "rule", "content": "r1"})
        adapter.put("s2", {"kind": "note", "content": "n1"})
        rules = adapter.scan("rule")
        assert len(rules) == 1
        assert rules[0].kind == "rule"

    def test_clear(self, tmp_path: Path) -> None:
        adapter = self._make_adapter(tmp_path)
        adapter.put("c1", {"kind": "x", "content": "1"})
        adapter.clear()
        assert adapter.count() == 0

    def test_flush_and_load_are_noops(self, tmp_path: Path) -> None:
        adapter = self._make_adapter(tmp_path)
        adapter.flush()  # should not raise
        adapter.load()   # should not raise

    def test_store_property_exposes_underlying_store(self, tmp_path: Path) -> None:
        adapter = self._make_adapter(tmp_path)
        from memory.store import MemoryStore

        assert isinstance(adapter.store, MemoryStore)

    def test_implements_protocol(self, tmp_path: Path) -> None:
        adapter = self._make_adapter(tmp_path)
        # MemoryStoreAdapter should satisfy the StorageBackend protocol
        assert hasattr(adapter, "put")
        assert hasattr(adapter, "get")
        assert hasattr(adapter, "delete")
        assert hasattr(adapter, "scan")
        assert hasattr(adapter, "keys")
        assert hasattr(adapter, "flush")
        assert hasattr(adapter, "load")
        assert hasattr(adapter, "clear")
        assert hasattr(adapter, "count")
