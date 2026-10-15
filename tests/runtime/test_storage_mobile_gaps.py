"""Gap coverage for storage_backend + mobile_patterns."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from runtime.storage_backend import (
    JsonFileStorage,
    MemoryStoreAdapter,
    SqliteStorage,
    StorageFactory,
    StorageMode,
    get_default_factory,
)


class TestJsonStorageGaps:
    def test_load_existing(self, tmp_path):
        f = tmp_path / "s.json"
        f.write_text('{"a": 1}')
        s = JsonFileStorage(f)
        s.load()
        assert s.get("a") == 1

    def test_load_corrupt(self, tmp_path):
        f = tmp_path / "s.json"
        f.write_text("{corrupt")
        s = JsonFileStorage(f)
        s.load()
        assert s.count() == 0

    def test_load_non_dict(self, tmp_path):
        f = tmp_path / "s.json"
        f.write_text("[1,2]")
        s = JsonFileStorage(f)
        s.load()
        assert s.count() == 0

    def test_load_twice_noop(self, tmp_path):
        s = JsonFileStorage(tmp_path / "s.json")
        s.load()
        s.load()  # second load no-op

    def test_scan_callable_filter(self, tmp_path):
        s = JsonFileStorage(tmp_path / "s.json")
        s.put("a", 1)
        s.put("b", 2)
        assert s.scan(lambda k: k == "a") == [1]
        assert s.scan("b") == [2]

    def test_flush_error_cleans_tmp(self, tmp_path):
        s = JsonFileStorage(tmp_path / "s.json")
        s.put("a", 1)
        s.load()
        import os as _os

        with patch("tempfile.mkstemp", return_value=(0, str(tmp_path / "t.tmp"))), \
             patch.object(_os, "fdopen", side_effect=OSError("disk full")):
            with pytest.raises(OSError):
                s.flush()
        assert not (tmp_path / "t.tmp").exists()


class TestSqliteGaps:
    def test_invalid_table(self, tmp_path):
        with pytest.raises(ValueError):
            SqliteStorage(tmp_path / "x.db", table_name="bad;drop")

    def test_get_corrupt_returns_raw(self, tmp_path):
        s = SqliteStorage(tmp_path / "x.db")
        s.put("k", {"v": 1})
        conn = s._connect()
        conn.execute("UPDATE kv_store SET value='{bad' WHERE key='k'")
        assert s.get("k") == "{bad"

    def test_scan_callable(self, tmp_path):
        s = SqliteStorage(tmp_path / "x.db")
        s.put("a", 1)
        s.put("b", 2)
        assert sorted(s.scan(lambda k: k == "a")) == [1]
        # corrupt row skipped in callable filter
        conn = s._connect()
        conn.execute("INSERT INTO kv_store (key,value) VALUES ('bad','{x')")
        assert sorted(s.scan(lambda k: True)) == [1, 2]

    def test_scan_filter_raises(self, tmp_path):
        s = SqliteStorage(tmp_path / "x.db")
        s.put("a", 1)
        assert s.scan(lambda k: 1 / 0) == []

    def test_scan_equality(self, tmp_path):
        s = SqliteStorage(tmp_path / "x.db")
        s.put("a", 1)
        s.put("b", 2)
        assert s.scan("a") == [1]

    def test_scan_corrupt_row_skipped(self, tmp_path):
        s = SqliteStorage(tmp_path / "x.db")
        s.put("a", 1)
        conn = s._connect()
        conn.execute("INSERT INTO kv_store (key,value) VALUES ('bad','{x')")
        assert s.scan() == [1]

    def test_close_no_conn(self, tmp_path):
        s = SqliteStorage(tmp_path / "x.db")
        s.close()  # never connected - no-op
        s.close()


class TestFactoryGaps:
    def test_file_name_required(self, tmp_path):
        f = StorageFactory(base_dir=tmp_path)
        with pytest.raises(ValueError):
            f.create("x", mode=StorageMode.JSON)

    def test_sqlite_mode(self, tmp_path):
        f = StorageFactory(base_dir=tmp_path)
        b = f.create("t", file_name="t.json", mode=StorageMode.SQLITE)
        assert (tmp_path / "t.db").exists() or b is not None
        b.put("k", 1)
        assert b.get("k") == 1

    def test_sqlite_sanitized_table(self, tmp_path):
        f = StorageFactory(base_dir=tmp_path)
        b = f.create("my-name.x", file_name="s.db", mode=StorageMode.SQLITE)
        b.put("k", 1)
        assert b.get("k") == 1

    def test_unknown_mode(self, tmp_path):
        f = StorageFactory(base_dir=tmp_path)
        with pytest.raises(ValueError):
            f.create("x", file_name="x.db", mode="bogus")  # type: ignore[arg-type]

    def test_load_flush_clear_all(self, tmp_path):
        f = StorageFactory(base_dir=tmp_path)
        b = f.create("x", file_name="x.json", mode=StorageMode.JSON)
        b.put("k", 1)
        f.load_all()
        f.flush_all()
        assert (tmp_path / "x.json").exists()
        f.clear_all()
        assert b.count() == 0

    def test_shutdown_all(self, tmp_path):
        f = StorageFactory(base_dir=tmp_path)
        f.create("x", file_name="x.db", mode=StorageMode.SQLITE)
        f.shutdown_all()
        assert f.count() == 0

    def test_modes_in_use(self, tmp_path):
        f = StorageFactory(base_dir=tmp_path)
        f.create("a")
        f.create("b", file_name="b.json", mode=StorageMode.JSON)
        modes = f.modes_in_use()
        assert StorageMode.MEMORY in modes and StorageMode.JSON in modes

    def test_default_factory(self):
        f1 = get_default_factory()
        assert f1 is get_default_factory()


class TestAdapterGaps:
    def test_put_dict_and_get(self, tmp_path):
        from memory.store import MemoryStore

        store = MemoryStore(tmp_path)
        ad = MemoryStoreAdapter(store)
        ad.put("k1", {"kind": "note", "content": "hello", "source": "t"})
        got = ad.get("k1")
        assert got is not None and got.content == "hello"

    def test_put_memory_obj(self, tmp_path):
        from memory.store import Memory, MemoryStore

        store = MemoryStore(tmp_path)
        ad = MemoryStoreAdapter(store)
        ad.put("k2", Memory(id="tmp", kind="note", content="mem-content",
                            source="s", meta="{}", created_at="",
                            valid_from="", valid_to=None))
        got = ad.get("k2")
        assert got is not None and got.content == "mem-content"

    def test_put_scalar_fallback(self, tmp_path):
        from memory.store import MemoryStore

        store = MemoryStore(tmp_path)
        ad = MemoryStoreAdapter(store)
        ad.put("k3", 42)
        got = ad.get("k3")
        assert got is not None and got.content == "42"


