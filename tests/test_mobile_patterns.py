"""Tests for runtime/mobile_patterns.py — Mobile app pattern auditing.

Tests cover all 18 pattern checks for both Flutter and React Native
platforms, plus audit_summary and edge cases.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from runtime.mobile_patterns import (
    MobileAuditConfig,
    MobilePattern,
    MobilePatternAuditor,
    MobilePlatform,
    PatternResult,
    PatternSeverity,
)
from runtime.schemas import ValidationError

# -- Fixtures ----------------------------------------------------------------


@pytest.fixture
def flutter_project(tmp_path: Path) -> Path:
    """Create a minimal Flutter project structure."""
    (tmp_path / "lib" / "features" / "auth" / "domain").mkdir(parents=True)
    (tmp_path / "lib" / "features" / "auth" / "data").mkdir(parents=True)
    (tmp_path / "lib" / "features" / "auth" / "presentation").mkdir(parents=True)
    (tmp_path / "lib" / "core" / "router").mkdir(parents=True)
    (tmp_path / "lib" / "core" / "errors").mkdir(parents=True)
    (tmp_path / "lib" / "design_system").mkdir(parents=True)
    (tmp_path / "lib" / "shared" / "widgets").mkdir(parents=True)
    (tmp_path / "test").mkdir(parents=True)
    (tmp_path / "integration_test").mkdir(parents=True)
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / "pubspec.yaml").write_text(
        "name: my_app\nenvironment:\n  sdk: '>=3.13.0 <4.0.0'\n"
        "dependencies:\n  flutter_riverpod: ^3.3.1\n  go_router: ^17.2.0\n"
        "  go_router_builder: ^4.2.0\n  freezed: ^3.2.5\n  drift: ^2.20.0\n"
        "  flutter_secure_storage: ^10.0.0\n  sentry_flutter: ^9.16.0\n"
        "  posthog_flutter: ^5.23.0\n  flutter_localizations: ^0.0.1\n",
        encoding="utf-8",
    )
    (tmp_path / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")
    # Router with refresh pattern
    (tmp_path / "lib" / "core" / "router" / "app_router.dart").write_text(
        "class _RouterRefreshNotifier extends ChangeNotifier {\n"
        "  void notify() => notifyListeners();\n"
        "}\n"
        "GoRouter(refreshListenable: notifier);\n",
        encoding="utf-8",
    )
    # Freezed failure
    (tmp_path / "lib" / "core" / "errors" / "failure.dart").write_text(
        "@freezed\nclass Failure with _$Failure {\n"
        "  const factory Failure.network() = NetworkFailure;\n}\n",
        encoding="utf-8",
    )
    # Type-safe routing
    (tmp_path / "lib" / "core" / "router" / "routes.dart").write_text(
        "@TypedGoRoute<RootRoute>(path: '/')\nclass RootRoute extends GoRouteData {}\n",
        encoding="utf-8",
    )
    # UseCase
    (tmp_path / "lib" / "features" / "auth" / "domain" / "use_case.dart").write_text(
        "abstract class UseCase<R, P> { Future<Result<R>> call(P p); }\n",
        encoding="utf-8",
    )
    # Design tokens
    (tmp_path / "lib" / "design_system" / "tokens.dart").write_text(
        "class AppColors { static const primary = Color(0x4F46E5FF); }\n",
        encoding="utf-8",
    )
    # Shared widgets
    (tmp_path / "lib" / "shared" / "widgets" / "button.dart").write_text(
        "class AppButton extends StatelessWidget {}\n",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def rn_project(tmp_path: Path) -> Path:
    """Create a minimal React Native / Expo project structure."""
    (tmp_path / "app").mkdir(parents=True)
    (tmp_path / "src" / "features" / "auth" / "components").mkdir(parents=True)
    (tmp_path / "src" / "features" / "auth" / "services").mkdir(parents=True)
    (tmp_path / "src" / "common" / "components").mkdir(parents=True)
    (tmp_path / "src" / "theme").mkdir(parents=True)
    (tmp_path / "src" / "providers").mkdir(parents=True)
    (tmp_path / "__tests__").mkdir(parents=True)
    (tmp_path / ".maestro").mkdir(parents=True)
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / "package.json").write_text(
        '{"dependencies": {"expo": "^56.0.0", "react-native": "0.86.0",'
        ' "@tanstack/react-query": "^5.90.0", "zustand": "^5.0.0",'
        ' "react-native-mmkv": "^4.0.0", "expo-secure-store": "^14.0.0",'
        ' "react-native-unistyles": "^3.0.0", "i18next": "^23.0.0",'
        ' "react-i18next": "^15.0.0", "@sentry/react-native": "^6.0.0",'
        ' "posthog-react-native": "^3.0.0", "axios": "^1.7.0"}}',
        encoding="utf-8",
    )
    (tmp_path / "app.json").write_text(
        '{"expo": {"name": "MyApp", "experiments": {"typedRoutes": true}}}',
        encoding="utf-8",
    )
    (tmp_path / "eas.json").write_text('{"build": {"production": {}}}', encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")
    # Ordered logout
    (tmp_path / "src" / "features" / "auth" / "services" / "auth.ts").write_text(
        "async function logout() {\n"
        "  await queryClient.cancelQueries();\n"
        "  posthog.reset();\n"
        "  queryClient.clear();\n"
        "  await supabase.auth.signOut();\n"
        "}\n",
        encoding="utf-8",
    )
    # Cache buster
    (tmp_path / "src" / "providers" / "query.ts").write_text(
        "function getQueryCacheBuster(userId: string) { return `user:${userId}`; }\n",
        encoding="utf-8",
    )
    # Theme tokens
    (tmp_path / "src" / "theme" / "tokens.ts").write_text(
        "export const colors = { primary: '#4F46E5' };\n",
        encoding="utf-8",
    )
    # Components
    (tmp_path / "src" / "common" / "components" / "Button.tsx").write_text(
        "export function Button() { return null; }\n",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def empty_project(tmp_path: Path) -> Path:
    """Create an empty project directory."""
    return tmp_path


# -- Config validation tests -------------------------------------------------


class TestMobileAuditConfig:
    def test_valid_config(self, tmp_path: Path) -> None:
        config = MobileAuditConfig(platform=MobilePlatform.FLUTTER, project_root=tmp_path)
        assert config.platform == MobilePlatform.FLUTTER
        assert config.project_root == tmp_path
        assert config.check_patterns is None

    def test_nonexistent_root_raises(self, tmp_path: Path) -> None:
        bad_path = tmp_path / "nonexistent"
        with pytest.raises(ValidationError, match="does not exist"):
            MobileAuditConfig(platform=MobilePlatform.FLUTTER, project_root=bad_path)

    def test_file_as_root_raises(self, tmp_path: Path) -> None:
        file_path = tmp_path / "file.txt"
        file_path.write_text("test", encoding="utf-8")
        with pytest.raises(ValidationError, match="not a directory"):
            MobileAuditConfig(platform=MobilePlatform.FLUTTER, project_root=file_path)

    def test_custom_check_patterns(self, tmp_path: Path) -> None:
        patterns = {MobilePattern.FEATURE_FIRST_ARCHITECTURE, MobilePattern.CI_CD_PIPELINE}
        config = MobileAuditConfig(
            platform=MobilePlatform.FLUTTER, project_root=tmp_path, check_patterns=patterns,
        )
        assert config.check_patterns == patterns


# -- PatternResult tests -----------------------------------------------------


class TestPatternResult:
    def test_to_dict_passed(self) -> None:
        result = PatternResult(MobilePattern.CI_CD_PIPELINE, True, message="OK")
        d = result.to_dict()
        assert d["pattern"] == "ci_cd_pipeline"
        assert d["passed"] is True
        assert d["severity"] == "info"
        assert d["message"] == "OK"
        assert d["file_hint"] is None

    def test_to_dict_failed_critical(self) -> None:
        result = PatternResult(
            MobilePattern.SECURE_TOKEN_STORAGE, False,
            PatternSeverity.CRITICAL, "Missing", "pubspec.yaml",
        )
        d = result.to_dict()
        assert d["passed"] is False
        assert d["severity"] == "critical"
        assert d["file_hint"] == "pubspec.yaml"


# -- Flutter pattern tests ---------------------------------------------------


class TestFlutterPatterns:
    def test_feature_first_pass(self, flutter_project: Path) -> None:
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.FLUTTER, flutter_project))
        result = auditor._check_feature_first()
        assert result.passed is True

    def test_feature_first_fail(self, empty_project: Path) -> None:
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.FLUTTER, empty_project))
        result = auditor._check_feature_first()
        assert result.passed is False
        assert result.severity == PatternSeverity.CRITICAL

    def test_clean_layering_pass(self, flutter_project: Path) -> None:
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.FLUTTER, flutter_project))
        result = auditor._check_clean_layering()
        assert result.passed is True

    def test_clean_layering_fail(self, tmp_path: Path) -> None:
        (tmp_path / "lib" / "features" / "auth").mkdir(parents=True)
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.FLUTTER, tmp_path))
        result = auditor._check_clean_layering()
        assert result.passed is False

    def test_router_refresh_pass(self, flutter_project: Path) -> None:
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.FLUTTER, flutter_project))
        result = auditor._check_router_refresh()
        assert result.passed is True

    def test_router_refresh_fail(self, empty_project: Path) -> None:
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.FLUTTER, empty_project))
        result = auditor._check_router_refresh()
        assert result.passed is False

    def test_freezed_failure_pass(self, flutter_project: Path) -> None:
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.FLUTTER, flutter_project))
        result = auditor._check_freezed_failure()
        assert result.passed is True

    def test_freezed_failure_fail(self, empty_project: Path) -> None:
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.FLUTTER, empty_project))
        result = auditor._check_freezed_failure()
        assert result.passed is False

    def test_type_safe_routing_pass(self, flutter_project: Path) -> None:
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.FLUTTER, flutter_project))
        result = auditor._check_type_safe_routing()
        assert result.passed is True

    def test_usecase_pass(self, flutter_project: Path) -> None:
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.FLUTTER, flutter_project))
        result = auditor._check_usecase_pattern()
        assert result.passed is True

    def test_usecase_fail(self, empty_project: Path) -> None:
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.FLUTTER, empty_project))
        result = auditor._check_usecase_pattern()
        assert result.passed is False

    def test_offline_first_pass(self, flutter_project: Path) -> None:
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.FLUTTER, flutter_project))
        result = auditor._check_offline_first()
        assert result.passed is True

    def test_secure_storage_pass(self, flutter_project: Path) -> None:
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.FLUTTER, flutter_project))
        result = auditor._check_secure_storage()
        assert result.passed is True

    def test_secure_storage_fail(self, empty_project: Path) -> None:
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.FLUTTER, empty_project))
        result = auditor._check_secure_storage()
        assert result.passed is False
        assert result.severity == PatternSeverity.CRITICAL

    def test_design_tokens_pass(self, flutter_project: Path) -> None:
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.FLUTTER, flutter_project))
        result = auditor._check_design_tokens()
        assert result.passed is True

    def test_i18n_pass(self, flutter_project: Path) -> None:
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.FLUTTER, flutter_project))
        result = auditor._check_i18n_rtl()
        assert result.passed is True

    def test_two_tier_testing_pass(self, flutter_project: Path) -> None:
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.FLUTTER, flutter_project))
        result = auditor._check_two_tier_testing()
        assert result.passed is True

    def test_two_tier_testing_fail_no_e2e(self, tmp_path: Path) -> None:
        (tmp_path / "test").mkdir()
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.FLUTTER, tmp_path))
        result = auditor._check_two_tier_testing()
        assert result.passed is False

    def test_ai_instructions_pass(self, flutter_project: Path) -> None:
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.FLUTTER, flutter_project))
        result = auditor._check_ai_instructions()
        assert result.passed is True

    def test_component_library_pass(self, flutter_project: Path) -> None:
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.FLUTTER, flutter_project))
        result = auditor._check_component_library()
        assert result.passed is True

    def test_observability_pass(self, flutter_project: Path) -> None:
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.FLUTTER, flutter_project))
        result = auditor._check_observability()
        assert result.passed is True

    def test_ci_cd_pass(self, flutter_project: Path) -> None:
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.FLUTTER, flutter_project))
        result = auditor._check_ci_cd()
        assert result.passed is True

    def test_ci_cd_fastfile_nested(self, tmp_path: Path) -> None:
        """CI/CD via fastlane/Fastfile (nested) should be detected."""
        (tmp_path / "ios" / "fastlane").mkdir(parents=True)
        (tmp_path / "ios" / "fastlane" / "Fastfile").write_text("lane :beta do\nend\n", encoding="utf-8")
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.FLUTTER, tmp_path))
        result = auditor._check_ci_cd()
        assert result.passed is True

    def test_ci_cd_fastfile_root(self, tmp_path: Path) -> None:
        """CI/CD via root-level fastlane/ dir should be detected."""
        (tmp_path / "fastlane").mkdir()
        (tmp_path / "fastlane" / "Fastfile").write_text("lane :beta do\nend\n", encoding="utf-8")
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.FLUTTER, tmp_path))
        result = auditor._check_ci_cd()
        assert result.passed is True

    def test_backend_isolation_pass(self, flutter_project: Path) -> None:
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.FLUTTER, flutter_project))
        result = auditor._check_backend_isolation()
        assert result.passed is True

    def test_backend_isolation_fail(self, tmp_path: Path) -> None:
        feat = tmp_path / "lib" / "features" / "auth" / "domain"
        feat.mkdir(parents=True)
        (feat / "entity.dart").write_text(
            "import 'package:firebase_auth/firebase_auth.dart';\n", encoding="utf-8",
        )
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.FLUTTER, tmp_path))
        result = auditor._check_backend_isolation()
        assert result.passed is False
        assert result.severity == PatternSeverity.CRITICAL

    def test_backend_isolation_rn_pass(self, rn_project: Path) -> None:
        """RN: backend SDK in services/ only — should pass."""
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.REACT_NATIVE, rn_project))
        result = auditor._check_backend_isolation()
        assert result.passed is True

    def test_backend_isolation_rn_fail(self, tmp_path: Path) -> None:
        """RN: @supabase in components/ — should fail."""
        comp = tmp_path / "src" / "features" / "auth" / "components"
        comp.mkdir(parents=True)
        (comp / "LoginButton.ts").write_text(
            "import { createClient } from '@supabase/supabase-js';\n", encoding="utf-8",
        )
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.REACT_NATIVE, tmp_path))
        result = auditor._check_backend_isolation()
        assert result.passed is False
        assert result.severity == PatternSeverity.CRITICAL


# -- React Native pattern tests ----------------------------------------------


class TestReactNativePatterns:
    def test_feature_first_pass(self, rn_project: Path) -> None:
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.REACT_NATIVE, rn_project))
        result = auditor._check_feature_first()
        assert result.passed is True

    def test_feature_first_fail(self, empty_project: Path) -> None:
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.REACT_NATIVE, empty_project))
        result = auditor._check_feature_first()
        assert result.passed is False

    def test_offline_first_pass(self, rn_project: Path) -> None:
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.REACT_NATIVE, rn_project))
        result = auditor._check_offline_first()
        assert result.passed is True

    def test_secure_storage_pass(self, rn_project: Path) -> None:
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.REACT_NATIVE, rn_project))
        result = auditor._check_secure_storage()
        assert result.passed is True

    def test_ordered_logout_pass(self, rn_project: Path) -> None:
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.REACT_NATIVE, rn_project))
        result = auditor._check_ordered_logout()
        assert result.passed is True

    def test_ordered_logout_fail(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.REACT_NATIVE, tmp_path))
        result = auditor._check_ordered_logout()
        assert result.passed is False

    def test_query_cache_buster_pass(self, rn_project: Path) -> None:
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.REACT_NATIVE, rn_project))
        result = auditor._check_query_cache_buster()
        assert result.passed is True

    def test_design_tokens_pass(self, rn_project: Path) -> None:
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.REACT_NATIVE, rn_project))
        result = auditor._check_design_tokens()
        assert result.passed is True

    def test_i18n_pass(self, rn_project: Path) -> None:
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.REACT_NATIVE, rn_project))
        result = auditor._check_i18n_rtl()
        assert result.passed is True

    def test_two_tier_testing_pass(self, rn_project: Path) -> None:
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.REACT_NATIVE, rn_project))
        result = auditor._check_two_tier_testing()
        assert result.passed is True

    def test_type_safe_routing_pass(self, rn_project: Path) -> None:
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.REACT_NATIVE, rn_project))
        result = auditor._check_type_safe_routing()
        assert result.passed is True

    def test_ci_cd_pass(self, rn_project: Path) -> None:
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.REACT_NATIVE, rn_project))
        result = auditor._check_ci_cd()
        assert result.passed is True

    def test_observability_pass(self, rn_project: Path) -> None:
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.REACT_NATIVE, rn_project))
        result = auditor._check_observability()
        assert result.passed is True

    def test_component_library_pass(self, rn_project: Path) -> None:
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.REACT_NATIVE, rn_project))
        result = auditor._check_component_library()
        assert result.passed is True

    def test_router_refresh_skipped(self, rn_project: Path) -> None:
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.REACT_NATIVE, rn_project))
        result = auditor._check_router_refresh()
        assert result.passed is False  # Flutter-only pattern, not in RN applicable set


# -- Audit and summary tests -------------------------------------------------


class TestAuditAndSummary:
    def test_audit_returns_results(self, flutter_project: Path) -> None:
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.FLUTTER, flutter_project))
        results = auditor.audit()
        assert len(results) > 0
        assert all(isinstance(r, PatternResult) for r in results)

    def test_audit_all_patterns_flutter(self, flutter_project: Path) -> None:
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.FLUTTER, flutter_project))
        results = auditor.audit()
        patterns_checked = {r.pattern for r in results}
        assert MobilePattern.FEATURE_FIRST_ARCHITECTURE in patterns_checked
        assert MobilePattern.CI_CD_PIPELINE in patterns_checked
        assert MobilePattern.ROUTER_REFRESH_PATTERN in patterns_checked

    def test_audit_custom_patterns(self, flutter_project: Path) -> None:
        config = MobileAuditConfig(
            MobilePlatform.FLUTTER, flutter_project,
            check_patterns={MobilePattern.CI_CD_PIPELINE, MobilePattern.SECURE_TOKEN_STORAGE},
        )
        auditor = MobilePatternAuditor(config)
        results = auditor.audit()
        assert len(results) == 2
        patterns = {r.pattern for r in results}
        assert patterns == {MobilePattern.CI_CD_PIPELINE, MobilePattern.SECURE_TOKEN_STORAGE}

    def test_audit_summary_structure(self, flutter_project: Path) -> None:
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.FLUTTER, flutter_project))
        summary = auditor.audit_summary()
        assert "platform" in summary
        assert "total" in summary
        assert "passed" in summary
        assert "failed" in summary
        assert "critical" in summary
        assert "warnings" in summary
        assert "score" in summary
        assert "results" in summary
        assert summary["platform"] == "flutter"
        assert summary["total"] > 0
        assert summary["total"] == summary["passed"] + summary["failed"]

    def test_audit_summary_score_calculation(self, flutter_project: Path) -> None:
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.FLUTTER, flutter_project))
        summary = auditor.audit_summary()
        expected_score = round(summary["passed"] / summary["total"] * 100, 1)
        assert summary["score"] == expected_score

    def test_audit_empty_project_low_score(self, empty_project: Path) -> None:
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.FLUTTER, empty_project))
        summary = auditor.audit_summary()
        assert summary["score"] < 50.0
        assert summary["critical"] > 0

    def test_audit_full_flutter_project_high_score(self, flutter_project: Path) -> None:
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.FLUTTER, flutter_project))
        summary = auditor.audit_summary()
        assert summary["score"] >= 80.0
        assert summary["critical"] == 0

    def test_audit_rn_project(self, rn_project: Path) -> None:
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.REACT_NATIVE, rn_project))
        summary = auditor.audit_summary()
        assert summary["platform"] == "react_native"
        assert summary["total"] > 0
        assert summary["score"] >= 70.0

    def test_audit_rn_skips_flutter_only_patterns(self, rn_project: Path) -> None:
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.REACT_NATIVE, rn_project))
        results = auditor.audit()
        patterns = {r.pattern for r in results}
        assert MobilePattern.ROUTER_REFRESH_PATTERN not in patterns
        assert MobilePattern.FREEZED_FAILURE_UNION not in patterns
        assert MobilePattern.USECASE_PATTERN not in patterns

    def test_audit_summary_results_are_dicts(self, flutter_project: Path) -> None:
        auditor = MobilePatternAuditor(MobileAuditConfig(MobilePlatform.FLUTTER, flutter_project))
        summary = auditor.audit_summary()
        assert all(isinstance(r, dict) for r in summary["results"])
        assert all("pattern" in r and "passed" in r for r in summary["results"])
