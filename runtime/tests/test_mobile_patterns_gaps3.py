"""Gap tests round 3 for runtime/mobile_patterns.py - walk/error edges."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

import runtime.mobile_patterns as mpm
from runtime.mobile_patterns import (
    MobileAuditConfig,
    MobilePattern,
    MobilePatternAuditor,
    MobilePlatform,
    _dir_contains_recursive,
    _iter_files_bounded,
)


class _FakeEntry:
    def __init__(self, path: Path, symlink_raises: bool = False) -> None:
        self.path = str(path)
        self.name = path.name
        self._raises = symlink_raises

    def is_symlink(self) -> bool:
        if self._raises:
            raise OSError("symlink check failed")
        return False


class _FakeScandir:
    def __init__(self, entries: list[_FakeEntry]) -> None:
        self._entries = entries

    def __enter__(self) -> list[_FakeEntry]:
        return self._entries

    def __exit__(self, *a: object) -> None:
        pass


def _auditor(tmp_path: Path, platform: MobilePlatform, patterns: set[MobilePattern]) -> MobilePatternAuditor:
    return MobilePatternAuditor(
        MobileAuditConfig(platform=platform, project_root=tmp_path, check_patterns=patterns)
    )


class TestIterWalkEdges:
    def test_symlinked_dir_skipped(self, tmp_path: Path) -> None:
        (tmp_path / "linked").mkdir()
        (tmp_path / "real").mkdir()
        (tmp_path / "real" / "f.dart").write_text("x")
        orig = Path.is_symlink

        def fake(self: Path) -> bool:
            return self.name == "linked" or orig(self)

        with patch.object(Path, "is_symlink", fake):
            out = _iter_files_bounded(tmp_path)
        assert tmp_path / "real" / "f.dart" in out

    def test_entry_symlink_oserror(self, tmp_path: Path) -> None:
        (tmp_path / "d").mkdir()
        (tmp_path / "d" / "f.dart").write_text("x")
        bad = _FakeEntry(tmp_path / "d" / "g.dart", symlink_raises=True)

        def scandir(path: object, *a: object, **k: object):
            if Path(str(path)) == tmp_path / "d":
                return _FakeScandir([bad])
            return _FakeScandir([])

        with patch.object(os, "scandir", scandir):
            out = _iter_files_bounded(tmp_path)
        assert out == []

    def test_neither_dir_nor_file(self, tmp_path: Path) -> None:
        (tmp_path / "d").mkdir()
        ghost = _FakeEntry(tmp_path / "d" / "ghost")

        def scandir(path: object, *a: object, **k: object):
            if Path(str(path)) == tmp_path / "d":
                return _FakeScandir([ghost])
            return _FakeScandir([])

        with patch.object(os, "scandir", scandir):
            assert _iter_files_bounded(tmp_path) == []

    def test_scan_file_cap(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        d = tmp_path / "lib"
        d.mkdir()
        for i in range(3):
            (d / f"f{i}.dart").write_text("needle")
        monkeypatch.setattr(mpm, "_MAX_SCAN_FILES", 0)
        assert _dir_contains_recursive(tmp_path, ["lib"], "needle") is False


class TestBackendIsolationEdges:
    def test_dart_outside_layers_ignored(self, tmp_path: Path) -> None:
        d = tmp_path / "lib" / "features" / "data"
        d.mkdir(parents=True)
        (d / "repo.dart").write_text("package:firebase x")
        aud = _auditor(tmp_path, MobilePlatform.FLUTTER, {MobilePattern.BACKEND_ISOLATION})
        res = aud._check_backend_isolation()
        assert res.passed is True

    def test_dart_read_oserror(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        d = tmp_path / "lib" / "features" / "auth" / "domain"
        d.mkdir(parents=True)
        (d / "svc.dart").write_text("package:firebase x")
        orig = Path.read_text

        def flaky(self: Path, *a: object, **k: object) -> str:
            if self.suffix == ".dart":
                raise OSError("denied")
            return orig(self, *a, **k)  # type: ignore[arg-type]

        monkeypatch.setattr(Path, "read_text", flaky)
        aud = _auditor(tmp_path, MobilePlatform.FLUTTER, {MobilePattern.BACKEND_ISOLATION})
        assert aud._check_backend_isolation().passed is True

    def test_dart_relative_to_valueerror(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        d = tmp_path / "lib" / "features" / "auth" / "domain"
        d.mkdir(parents=True)
        (d / "svc.dart").write_text("package:firebase x")
        orig = Path.relative_to

        def flaky(self: Path, *a: object) -> Path:
            if self.suffix == ".dart":
                raise ValueError("not relative")
            return orig(self, *a)  # type: ignore[arg-type]

        monkeypatch.setattr(Path, "relative_to", flaky)
        aud = _auditor(tmp_path, MobilePlatform.FLUTTER, {MobilePattern.BACKEND_ISOLATION})
        assert aud._check_backend_isolation().passed is False

    def test_rn_read_oserror(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        d = tmp_path / "src" / "features" / "x" / "components"
        d.mkdir(parents=True)
        (d / "W.tsx").write_text('import "@supabase/supabase-js"')
        orig = Path.read_text

        def flaky(self: Path, *a: object, **k: object) -> str:
            if self.suffix == ".tsx":
                raise OSError("denied")
            return orig(self, *a, **k)  # type: ignore[arg-type]

        monkeypatch.setattr(Path, "read_text", flaky)
        aud = _auditor(tmp_path, MobilePlatform.REACT_NATIVE, {MobilePattern.BACKEND_ISOLATION})
        assert aud._check_backend_isolation().passed is True

    def test_rn_relative_to_valueerror(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        d = tmp_path / "src" / "features" / "x" / "components"
        d.mkdir(parents=True)
        (d / "W.tsx").write_text('import "@supabase/supabase-js"')
        orig = Path.relative_to

        def flaky(self: Path, *a: object) -> Path:
            if self.suffix == ".tsx":
                raise ValueError("not relative")
            return orig(self, *a)  # type: ignore[arg-type]

        monkeypatch.setattr(Path, "relative_to", flaky)
        aud = _auditor(tmp_path, MobilePlatform.REACT_NATIVE, {MobilePattern.BACKEND_ISOLATION})
        assert aud._check_backend_isolation().passed is False


class TestExpoAndPlatformEdges:
    def test_experiments_without_typed_routes(self, tmp_path: Path) -> None:
        (tmp_path / "app.json").write_text('{"expo": {"experiments": {"other": true}}}')
        aud = _auditor(tmp_path, MobilePlatform.REACT_NATIVE, {MobilePattern.TYPE_SAFE_ROUTING})
        assert aud._has_expo_typed_routes() is False

    def test_ordered_logout_non_rn(self, tmp_path: Path) -> None:
        aud = _auditor(tmp_path, MobilePlatform.FLUTTER, {MobilePattern.ORDERED_LOGOUT_CLEANUP})
        res = aud._check_ordered_logout()
        assert res.passed is False

    def test_query_cache_buster_non_rn(self, tmp_path: Path) -> None:
        aud = _auditor(tmp_path, MobilePlatform.FLUTTER, {MobilePattern.QUERY_CACHE_BUSTER})
        res = aud._check_query_cache_buster()
        assert res.passed is False
