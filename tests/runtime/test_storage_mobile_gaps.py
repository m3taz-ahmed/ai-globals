"""Gap coverage for storage_backend + mobile_patterns."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from runtime.mobile_patterns import (
    MobileAuditConfig,
    MobilePattern,
    MobilePatternAuditor,
    MobilePlatform,
    _applicable_patterns,
    _dir_contains_recursive,
    _iter_files_bounded,
    _rglob_exists,
)
from runtime.schemas import ValidationError
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


class TestMobileGaps:
    def test_kmp_swift_kotlin_patterns(self):
        assert _applicable_patterns(MobilePlatform.KOTLIN_MULTIPLATFORM)
        assert _applicable_patterns(MobilePlatform.SWIFT)
        assert _applicable_patterns(MobilePlatform.KOTLIN_NATIVE)

    def test_config_validation(self, tmp_path):
        with pytest.raises(ValidationError):
            MobileAuditConfig(MobilePlatform.FLUTTER, tmp_path / "nope")
        f = tmp_path / "file"
        f.write_text("x")
        with pytest.raises(ValidationError):
            MobileAuditConfig(MobilePlatform.FLUTTER, f)

    def test_iter_skip_dirs(self, tmp_path):
        (tmp_path / "node_modules").mkdir()
        (tmp_path / "node_modules" / "x.ts").write_text("x")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "ok.ts").write_text("x")
        files = _iter_files_bounded(tmp_path)
        assert any("ok.ts" in str(f) for f in files)
        assert not any("node_modules" in str(f) for f in files)

    def test_iter_pattern(self, tmp_path):
        (tmp_path / "a.dart").write_text("x")
        (tmp_path / "b.ts").write_text("x")
        files = _iter_files_bounded(tmp_path, "*.dart")
        assert len(files) == 1 and files[0].name == "a.dart"

    def test_dir_contains_recursive_file_base(self, tmp_path):
        (tmp_path / "x.dart").write_text("needle")
        assert _dir_contains_recursive(tmp_path, ["x.dart"], "NEEDLE")

    def test_dir_contains_missing(self, tmp_path):
        assert not _dir_contains_recursive(tmp_path, ["missing"], "x")

    def test_dir_contains_ts_suffix(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "a.tsx").write_text("NEEDLE")
        assert _dir_contains_recursive(tmp_path, ["src"], "needle", suffix=".ts")

    def test_rglob_exists(self, tmp_path):
        (tmp_path / "d").mkdir()
        (tmp_path / "d" / "f.go_router.dart").write_text("x")
        assert _rglob_exists(tmp_path, ["d"], "*router*.dart")
        assert not _rglob_exists(tmp_path, ["d"], "*.rs")
        assert not _rglob_exists(tmp_path, ["missing"], "*")

    def test_audit_all_platforms(self, tmp_path):
        for plat in (MobilePlatform.KOTLIN_MULTIPLATFORM,
                     MobilePlatform.SWIFT, MobilePlatform.KOTLIN_NATIVE):
            cfg = MobileAuditConfig(plat, tmp_path)
            summary = MobilePatternAuditor(cfg).audit_summary()
            assert summary["platform"] == plat.value
            assert summary["total"] > 0

    def test_audit_subset_patterns(self, tmp_path):
        cfg = MobileAuditConfig(
            MobilePlatform.FLUTTER, tmp_path,
            check_patterns={MobilePattern.FEATURE_FIRST_ARCHITECTURE})
        results = MobilePatternAuditor(cfg).audit()
        assert len(results) == 1

    def test_feature_first_flutter(self, tmp_path):
        (tmp_path / "lib" / "features").mkdir(parents=True)
        cfg = MobileAuditConfig(MobilePlatform.FLUTTER, tmp_path,
                                check_patterns={MobilePattern.FEATURE_FIRST_ARCHITECTURE})
        r = MobilePatternAuditor(cfg).audit()[0]
        assert r.passed

    def test_feature_first_rn(self, tmp_path):
        (tmp_path / "app.json").write_text("{}")
        cfg = MobileAuditConfig(MobilePlatform.REACT_NATIVE, tmp_path,
                                check_patterns={MobilePattern.FEATURE_FIRST_ARCHITECTURE})
        r = MobilePatternAuditor(cfg).audit()[0]
        assert r.passed
