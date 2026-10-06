"""Gap coverage for runtime/schemas.py + runtime/storage_backend.py edges."""

from __future__ import annotations

from pathlib import Path

import pytest

from runtime.schemas import (
    GateVerdict,
    PaginatedResult,
    PolicyDeniedError,
)
from runtime.storage_backend import (
    StorageFactory,
    StorageMode,
)


class TestSchemaEdges:
    def test_aizee_error_to_dict(self) -> None:
        err = PolicyDeniedError("nope", context={"a": 1})
        d = err.to_dict()
        assert d["error_code"] and d["message"] == "nope"

    def test_paginated_result_dict_and_has_more(self) -> None:
        p = PaginatedResult(items=[1, 2], next_token="tok", total=5)
        assert p.has_more is True
        d = p.to_dict()
        assert d["next_token"] == "tok" and d["total"] == 5
        p2 = PaginatedResult(items=[1])
        assert p2.has_more is False
        assert "next_token" not in p2.to_dict()

    def test_gate_verdict_bad_reason(self) -> None:
        with pytest.raises(TypeError, match="reason"):
            GateVerdict(gate="g", decision="allow", reason=123, metadata={}, spans=())  # type: ignore[arg-type]

    def test_gate_verdict_bad_metadata(self) -> None:
        with pytest.raises(TypeError, match="metadata"):
            GateVerdict(gate="g", decision="allow", reason="r", metadata="x", spans=())  # type: ignore[arg-type]


class TestStorageBackendEdges:
    def test_scan_equality_filter(self, tmp_path: Path) -> None:
        f = StorageFactory(base_dir=tmp_path)
        b = f.create("s1")
        b.put("k1", "v1")
        b.put("k2", "v2")
        assert b.scan("k1") == ["v1"]
        f.shutdown_all()

    def test_delete_missing_key(self, tmp_path: Path) -> None:
        f = StorageFactory(base_dir=tmp_path)
        b = f.create("s2")
        assert b.delete("ghost") is False
        f.shutdown_all()

    def test_sqlite_table_name_sanitized(self, tmp_path: Path) -> None:
        f = StorageFactory(base_dir=tmp_path, default_mode=StorageMode.SQLITE)
        b = f.create("123-abc", file_name="s3.db")
        b.put("k", "v")
        assert b.get("k") == "v"
        f.shutdown_all()

    def test_shutdown_closes_sqlite(self, tmp_path: Path) -> None:
        f = StorageFactory(base_dir=tmp_path)
        f.create("mem1")
        f.create("db1", file_name="d1.db", mode=StorageMode.SQLITE)
        f.create("mem2")
        f.shutdown_all()
        assert f._backends == []
