"""Gap coverage round 2: runtime/storage_backend.py remaining lines."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from runtime.storage_backend import (
    InMemoryStorage,
    JsonFileStorage,
    MemoryStoreAdapter,
    SqliteStorage,
    StorageFactory,
    StorageMode,
)


class TestInMemory:
    def test_full_cycle(self) -> None:
        s = InMemoryStorage()
        s.put("a", 1)
        s.put("b", 2)
        assert s.get("a") == 1 and s.get("zz") is None
        assert s.delete("a") is True and s.delete("a") is False
        assert s.scan() == [2]
        assert s.scan("b") == [2]
        assert s.scan(lambda k: k == "b") == [2]
        assert s.keys() == ["b"]
        s.flush()
        s.load()
        assert s.count() == 1
        s.clear()
        assert s.count() == 0


class TestJsonFile:
    def test_ops(self, tmp_path: Path) -> None:
        s = JsonFileStorage(tmp_path / "kv.json")
        s.put("a", {"v": 1})
        s.put("b", 2)
        assert s.delete("a") is True and s.delete("a") is False
        assert s.scan() == [2]
        assert s.scan("b") == [2]
        assert s.scan(lambda k: k == "b") == [2]
        assert s.keys() == ["b"]


class TestSqlite:
    def test_ops(self, tmp_path: Path) -> None:
        s = SqliteStorage(tmp_path / "kv.db")
        assert s.get("missing") is None
        s.put("j", {"x": 1})
        s.put("raw_key", "plain")
        # Corrupt the stored JSON for raw_key to hit the decode fallback.
        conn = s._connect()
        conn.execute("UPDATE kv_store SET value = '!!notjson' WHERE key = 'raw_key'")
        assert s.get("j") == {"x": 1}
        assert s.get("raw_key") == "!!notjson"
        assert s.delete("j") is True and s.delete("j") is False
        assert s.keys() == ["raw_key"]
        assert s.count() == 1
        s.clear()
        assert s.count() == 0
        s.flush()
        s.close()


class TestFactoryAndAdapter:
    def test_factory_same_path_cached(self, tmp_path: Path) -> None:
        f = StorageFactory(base_dir=tmp_path, default_mode=StorageMode.JSON)
        b1 = f.create("mystore", file_name="store.json")
        b2 = f.create("mystore", file_name="store.json")
        assert b1 is b2

    def test_memory_adapter(self) -> None:
        store = MagicMock()
        store.get.return_value = None
        adapter = MemoryStoreAdapter(store)
        assert adapter.delete("x") is False
        store.get.return_value = MagicMock(id="x")
        assert adapter.delete("x") is True
        store.invalidate.assert_called_with("x")
        adapter.scan("kind1")
        store.list_all.assert_called()
        adapter.keys()
        adapter.flush()
        adapter.load()
        adapter.count()
        adapter.clear()
        assert adapter.store is store
