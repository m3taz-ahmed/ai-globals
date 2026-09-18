"""Gap tests round 2 for runtime/mobile_patterns.py — helpers + RN branches."""

from __future__ import annotations

import contextlib
from pathlib import Path
from unittest.mock import patch

from runtime.mobile_patterns import (
    MobileAuditConfig,
    MobilePatternAuditor,
    MobilePlatform,
    _applicable_patterns,
    _dir_contains_recursive,
    _file_contains,
    _iter_files_bounded,
    _rglob_exists,
)


class TestIterFilesBounded:
    def test_symlink_skipped(self, tmp_path):
        real = tmp_path / "real.txt"
        real.write_text("x")
        link = tmp_path / "link.txt"
        with contextlib.suppress(OSError, NotImplementedError):
            link.symlink_to(real)  # Windows without privileges — symlink creation may fail
        out = _iter_files_bounded(tmp_path)
        assert real in out

    def test_is_symlink_oserror(self, tmp_path):
        f = tmp_path / "a.txt"
        f.write_text("x")
        orig = Path.is_symlink
        def flaky(self):
            if self.name == "a.txt":
                raise OSError("gone")
            return orig(self)
        with patch.object(Path, "is_symlink", flaky):
            out = _iter_files_bounded(tmp_path)
        assert f not in out

    def test_scandir_oserror(self, tmp_path):
        d = tmp_path / "sub"
        d.mkdir()
        with patch("os.scandir", side_effect=OSError("denied")):
            assert _iter_files_bounded(tmp_path) == []

    def test_skip_dirs(self, tmp_path):
        nm = tmp_path / "node_modules"
        nm.mkdir()
        (nm / "pkg.js").write_text("x")
        keep = tmp_path / "keep.js"
        keep.write_text("x")
        out = _iter_files_bounded(tmp_path)
        assert keep in out and not any("node_modules" in str(p) for p in out)

    def test_pattern_filter(self, tmp_path):
        (tmp_path / "a.dart").write_text("x")
        (tmp_path / "b.py").write_text("x")
        out = _iter_files_bounded(tmp_path, "*.dart")
        assert len(out) == 1 and out[0].name == "a.dart"

    def test_max_files(self, tmp_path):
        for i in range(10):
            (tmp_path / f"f{i}.txt").write_text("x")
        assert len(_iter_files_bounded(tmp_path, max_files=3)) == 3


class TestHelpers:
    def test_file_contains_missing(self, tmp_path):
        assert _file_contains(tmp_path, ["no", "file.txt"], "x") is False

    def test_file_contains_oserror(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("hello")
        with patch.object(Path, "read_text", side_effect=OSError("io")):
            assert _file_contains(tmp_path, ["f.txt"], "hello") is False

    def test_dir_contains_base_missing(self, tmp_path):
        assert _dir_contains_recursive(tmp_path, ["gone"], "x") is False

    def test_dir_contains_base_is_file(self, tmp_path):
        (tmp_path / "f.dart").write_text("import 'freezed'")
        assert _dir_contains_recursive(tmp_path, ["f.dart"], "freezed") is True

    def test_dir_contains_suffix_filter(self, tmp_path):
        d = tmp_path / "lib"
        d.mkdir()
        (d / "a.py").write_text("needle")
        (d / "b.dart").write_text("other")
        assert _dir_contains_recursive(tmp_path, ["lib"], "needle") is False
        assert _dir_contains_recursive(tmp_path, ["lib"], "other") is True

    def test_dir_contains_ts_covers_tsx(self, tmp_path):
        d = tmp_path / "src"
        d.mkdir()
        (d / "c.tsx").write_text("needle")
        assert _dir_contains_recursive(
            tmp_path, ["src"], "needle", suffix=".ts") is True

    def test_dir_contains_read_oserror(self, tmp_path):
        d = tmp_path / "lib"
        d.mkdir()
        (d / "a.dart").write_text("needle")
        with patch.object(Path, "read_text", side_effect=OSError("io")):
            assert _dir_contains_recursive(tmp_path, ["lib"], "needle") is False

    def test_rglob_missing_dir(self, tmp_path):
        assert _rglob_exists(tmp_path, ["gone"], "*.dart") is False


class TestPatternsFor:
    def test_kotlin_native(self):
        from runtime.mobile_patterns import _KOTLIN_PATTERNS
        assert _applicable_patterns(MobilePlatform.KOTLIN_NATIVE) == set(_KOTLIN_PATTERNS)

    def test_unknown_platform_fallback(self):
        from runtime.mobile_patterns import _KMP_PATTERNS
        assert _applicable_patterns("bogus") == set(_KMP_PATTERNS)


class TestAuditorRnBranches:
    def _rn_root(self, tmp_path) -> Path:
        (tmp_path / "src" / "features" / "feat" / "components").mkdir(parents=True)
        return tmp_path

    def test_rn_backend_isolation_no_features(self, tmp_path):
        a = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.REACT_NATIVE, tmp_path))
        r = a._check_backend_isolation()
        assert r.passed is True  # no src/features → pass with INFO

    def test_rn_backend_isolation_violation(self, tmp_path):
        root = self._rn_root(tmp_path)
        bad = root / "src" / "features" / "feat" / "components" / "c.tsx"
        bad.write_text("import { createClient } from '@supabase/supabase-js'")
        a = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.REACT_NATIVE, tmp_path))
        r = a._check_backend_isolation()
        assert r.passed is False

    def test_rn_backend_isolation_clean(self, tmp_path):
        root = self._rn_root(tmp_path)
        ok = root / "src" / "features" / "feat" / "components" / "c.tsx"
        ok.write_text("export const C = 1")
        a = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.REACT_NATIVE, tmp_path))
        assert a._check_backend_isolation().passed is True

    def test_rn_backend_isolation_non_ts(self, tmp_path):
        root = self._rn_root(tmp_path)
        f = root / "src" / "features" / "feat" / "components" / "c.js"
        f.write_text("import '@supabase/supabase-js'")
        a = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.REACT_NATIVE, tmp_path))
        assert a._check_backend_isolation().passed is True  # .js skipped

    def test_swift_backend_isolation_skip(self, tmp_path):
        a = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.SWIFT, tmp_path))
        r = a._check_backend_isolation()
        assert r.passed is False  # skipped → not ok, INFO

    def test_type_safe_routing_swift_skip(self, tmp_path):
        a = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.SWIFT, tmp_path))
        r = a._check_type_safe_routing()
        assert r.passed is False

    def test_expo_typed_routes(self, tmp_path):
        (tmp_path / "app.json").write_text(
            '{"expo": {"experiments": {"typedRoutes": true}}}')
        a = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.REACT_NATIVE, tmp_path))
        assert a._has_expo_typed_routes() is True

    def test_expo_typed_routes_top_level(self, tmp_path):
        (tmp_path / "app.json").write_text('{"expo": {"typedRoutes": true}}')
        a = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.REACT_NATIVE, tmp_path))
        assert a._has_expo_typed_routes() is True

    def test_expo_bad_json(self, tmp_path):
        (tmp_path / "app.json").write_text("{bad")
        (tmp_path / "app.config.json").write_text('{"expo": "notdict"}')
        a = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.REACT_NATIVE, tmp_path))
        assert a._has_expo_typed_routes() is False

    def test_expo_no_config(self, tmp_path):
        a = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.REACT_NATIVE, tmp_path))
        assert a._has_expo_typed_routes() is False

    def test_router_refresh_not_flutter(self, tmp_path):
        a = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.REACT_NATIVE, tmp_path))
        assert a._check_router_refresh().passed is False

    def test_freezed_not_flutter(self, tmp_path):
        a = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.REACT_NATIVE, tmp_path))
        assert a._check_freezed_failure().passed is False

    def test_usecase_not_flutter(self, tmp_path):
        a = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.SWIFT, tmp_path))
        assert a._check_usecase_pattern().passed is False

    def test_flutter_backend_isolation_violation(self, tmp_path):
        d = tmp_path / "lib" / "features" / "f" / "domain"
        d.mkdir(parents=True)
        (d / "repo.dart").write_text("import 'package:firebase/x.dart';")
        a = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.FLUTTER, tmp_path))
        assert a._check_backend_isolation().passed is False

    def test_flutter_backend_isolation_no_features(self, tmp_path):
        a = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.FLUTTER, tmp_path))
        assert a._check_backend_isolation().passed is False

    def test_flutter_router_refresh(self, tmp_path):
        d = tmp_path / "lib" / "core" / "router"
        d.mkdir(parents=True)
        (d / "app_router.dart").write_text(
            "final r = RouterRefreshNotifier(); // refreshListenable")
        a = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.FLUTTER, tmp_path))
        assert a._check_router_refresh().passed is True

    def test_flutter_freezed(self, tmp_path):
        (tmp_path / "pubspec.yaml").write_text("freezed: ^2.0")
        d = tmp_path / "lib" / "core"
        d.mkdir(parents=True)
        (d / "failure_types.dart").write_text("@freezed class Failure {}")
        a = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.FLUTTER, tmp_path))
        assert a._check_freezed_failure().passed is True

    def test_flutter_type_safe_routing(self, tmp_path):
        (tmp_path / "pubspec.yaml").write_text("go_router_builder: ^2.0")
        d = tmp_path / "lib"
        d.mkdir()
        (d / "routes.dart").write_text("TypedGoRoute<HomeRoute>")
        a = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.FLUTTER, tmp_path))
        assert a._check_type_safe_routing().passed is True

    def test_rn_type_safe_routing(self, tmp_path):
        (tmp_path / "app.json").write_text('{"expo": {"typedRoutes": true}}')
        a = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.REACT_NATIVE, tmp_path))
        assert a._check_type_safe_routing().passed is True

    def test_flutter_usecase(self, tmp_path):
        d = tmp_path / "lib" / "features" / "f" / "domain" / "usecases"
        d.mkdir(parents=True)
        (d / "use_case_get_user.dart").write_text("class GetUser {}")
        a = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.FLUTTER, tmp_path))
        assert a._check_usecase_pattern().passed is True
