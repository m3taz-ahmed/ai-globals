"""Mobile app architecture pattern validation and auditing.

Encodes patterns extracted from 8 production mobile repos (2026):
5 Flutter + 3 React Native/Expo. Validates that a mobile project
follows best-practice architecture, state management, security,
testing, CI/CD, and observability patterns.

Supported platforms: Flutter, React Native/Expo, Kotlin Multiplatform,
Swift (iOS native), Kotlin (Android native).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from runtime.schemas import ValidationError


class MobilePlatform(str, Enum):
    """Supported mobile platforms for pattern auditing."""

    FLUTTER = "flutter"
    REACT_NATIVE = "react_native"
    KOTLIN_MULTIPLATFORM = "kotlin_multiplatform"
    SWIFT = "swift"
    KOTLIN_NATIVE = "kotlin_native"


class MobilePattern(str, Enum):
    """Mobile architecture patterns to validate."""

    FEATURE_FIRST_ARCHITECTURE = "feature_first_architecture"
    CLEAN_LAYERING = "clean_layering"
    BACKEND_ISOLATION = "backend_isolation"
    ROUTER_REFRESH_PATTERN = "router_refresh_pattern"
    FREEZED_FAILURE_UNION = "freezed_failure_union"
    TYPE_SAFE_ROUTING = "type_safe_routing"
    USECASE_PATTERN = "usecase_pattern"
    OFFLINE_FIRST_SYNC = "offline_first_sync"
    SECURE_TOKEN_STORAGE = "secure_token_storage"
    ORDERED_LOGOUT_CLEANUP = "ordered_logout_cleanup"
    QUERY_CACHE_BUSTER = "query_cache_buster"
    DESIGN_TOKEN_SYSTEM = "design_token_system"
    I18N_WITH_RTL = "i18n_with_rtl"
    TWO_TIER_TESTING = "two_tier_testing"
    AI_INSTRUCTION_FILES = "ai_instruction_files"
    COMPONENT_LIBRARY = "component_library"
    OBSERVABILITY_WIRED = "observability_wired"
    CI_CD_PIPELINE = "ci_cd_pipeline"


class PatternSeverity(str, Enum):
    """Severity of a failed pattern check."""

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass
class PatternResult:
    """Result of a single pattern check.

    Attributes:
        pattern: The pattern that was checked.
        passed: Whether the pattern was satisfied.
        severity: Severity if the pattern failed.
        message: Human-readable description of the result.
        file_hint: Optional file path that should be inspected.
    """

    pattern: MobilePattern
    passed: bool
    severity: PatternSeverity = PatternSeverity.INFO
    message: str = ""
    file_hint: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for logging/API responses."""
        return {
            "pattern": self.pattern.value,
            "passed": self.passed,
            "severity": self.severity.value,
            "message": self.message,
            "file_hint": self.file_hint,
        }


@dataclass
class MobileAuditConfig:
    """Configuration for a mobile project audit.

    Attributes:
        platform: The mobile platform of the project.
        project_root: Root directory of the mobile project.
        check_patterns: Specific patterns to check (None = all applicable).
    """

    platform: MobilePlatform
    project_root: Path
    check_patterns: set[MobilePattern] | None = None

    def __post_init__(self) -> None:
        if not self.project_root.exists():
            raise ValidationError(
                f"Project root does not exist: {self.project_root}",
                context={"path": str(self.project_root)},
            )
        if not self.project_root.is_dir():
            raise ValidationError(
                f"Project root is not a directory: {self.project_root}",
                context={"path": str(self.project_root)},
            )


# -- Pattern applicability per platform ------------------------------------

_FLUTTER_PATTERNS: set[MobilePattern] = {
    MobilePattern.FEATURE_FIRST_ARCHITECTURE,
    MobilePattern.CLEAN_LAYERING,
    MobilePattern.BACKEND_ISOLATION,
    MobilePattern.ROUTER_REFRESH_PATTERN,
    MobilePattern.FREEZED_FAILURE_UNION,
    MobilePattern.TYPE_SAFE_ROUTING,
    MobilePattern.USECASE_PATTERN,
    MobilePattern.OFFLINE_FIRST_SYNC,
    MobilePattern.SECURE_TOKEN_STORAGE,
    MobilePattern.DESIGN_TOKEN_SYSTEM,
    MobilePattern.I18N_WITH_RTL,
    MobilePattern.TWO_TIER_TESTING,
    MobilePattern.AI_INSTRUCTION_FILES,
    MobilePattern.COMPONENT_LIBRARY,
    MobilePattern.OBSERVABILITY_WIRED,
    MobilePattern.CI_CD_PIPELINE,
}

_RN_PATTERNS: set[MobilePattern] = {
    MobilePattern.FEATURE_FIRST_ARCHITECTURE,
    MobilePattern.CLEAN_LAYERING,
    MobilePattern.BACKEND_ISOLATION,
    MobilePattern.OFFLINE_FIRST_SYNC,
    MobilePattern.SECURE_TOKEN_STORAGE,
    MobilePattern.ORDERED_LOGOUT_CLEANUP,
    MobilePattern.QUERY_CACHE_BUSTER,
    MobilePattern.DESIGN_TOKEN_SYSTEM,
    MobilePattern.I18N_WITH_RTL,
    MobilePattern.TWO_TIER_TESTING,
    MobilePattern.AI_INSTRUCTION_FILES,
    MobilePattern.COMPONENT_LIBRARY,
    MobilePattern.OBSERVABILITY_WIRED,
    MobilePattern.CI_CD_PIPELINE,
}


def _applicable_patterns(platform: MobilePlatform) -> set[MobilePattern]:
    """Return patterns applicable to the given platform."""
    if platform == MobilePlatform.FLUTTER:
        return _FLUTTER_PATTERNS
    if platform == MobilePlatform.REACT_NATIVE:
        return _RN_PATTERNS
    return _FLUTTER_PATTERNS | _RN_PATTERNS


# -- Helper utilities ------------------------------------------------------


def _has_dir(root: Path, *parts: str) -> bool:
    """Check if a directory exists under root."""
    return (root.joinpath(*parts)).is_dir()


def _has_file(root: Path, *parts: str) -> bool:
    """Check if a file exists under root."""
    return (root.joinpath(*parts)).is_file()


def _file_contains(root: Path, parts: list[str], needle: str) -> bool:
    """Check if a file contains a string (case-insensitive)."""
    path = root.joinpath(*parts)
    if not path.is_file():
        return False
    try:
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
    except OSError:
        return False
    return needle.lower() in text


def _dir_contains_recursive(root: Path, dir_parts: list[str], needle: str, suffix: str = ".dart") -> bool:
    """Check if any file under a directory contains a string (recursive)."""
    base = root.joinpath(*dir_parts)
    if not base.exists():
        return False
    if base.is_file():
        return _file_contains(root, dir_parts, needle)
    for f in base.rglob(f"*{suffix}"):
        try:
            text = f.read_text(encoding="utf-8", errors="ignore").lower()
        except OSError:
            continue
        if needle.lower() in text:
            return True
    return False


def _rglob_exists(root: Path, dir_parts: list[str], pattern: str) -> bool:
    """Check if any file matching a pattern exists recursively under a dir."""
    base = root.joinpath(*dir_parts)
    if not base.is_dir():
        return False
    return bool(list(base.rglob(pattern)))


# -- Auditor ---------------------------------------------------------------


class MobilePatternAuditor:
    """Audit a mobile project for architecture pattern compliance.

    Encodes best practices from 8 production mobile repos (2026):
    5 Flutter (ultimate-flutter-template, flutter-firebase-blueprint,
    flutter-riverpod-clean-arch, flutter-ddd-template, riverpod-clean-arch)
    and 3 React Native/Expo (expo-supabase-starter, expo-boilerplate-sdk56,
    rn-copilot).
    """

    def __init__(self, config: MobileAuditConfig) -> None:
        self.config = config
        self._root = config.project_root
        self._platform = config.platform
        self._all_patterns = config.check_patterns or _applicable_patterns(self._platform)

    def audit(self) -> list[PatternResult]:
        """Run all applicable pattern checks and return results."""
        check_map: dict[MobilePattern, Any] = {
            MobilePattern.FEATURE_FIRST_ARCHITECTURE: self._check_feature_first,
            MobilePattern.CLEAN_LAYERING: self._check_clean_layering,
            MobilePattern.BACKEND_ISOLATION: self._check_backend_isolation,
            MobilePattern.ROUTER_REFRESH_PATTERN: self._check_router_refresh,
            MobilePattern.FREEZED_FAILURE_UNION: self._check_freezed_failure,
            MobilePattern.TYPE_SAFE_ROUTING: self._check_type_safe_routing,
            MobilePattern.USECASE_PATTERN: self._check_usecase_pattern,
            MobilePattern.OFFLINE_FIRST_SYNC: self._check_offline_first,
            MobilePattern.SECURE_TOKEN_STORAGE: self._check_secure_storage,
            MobilePattern.ORDERED_LOGOUT_CLEANUP: self._check_ordered_logout,
            MobilePattern.QUERY_CACHE_BUSTER: self._check_query_cache_buster,
            MobilePattern.DESIGN_TOKEN_SYSTEM: self._check_design_tokens,
            MobilePattern.I18N_WITH_RTL: self._check_i18n_rtl,
            MobilePattern.TWO_TIER_TESTING: self._check_two_tier_testing,
            MobilePattern.AI_INSTRUCTION_FILES: self._check_ai_instructions,
            MobilePattern.COMPONENT_LIBRARY: self._check_component_library,
            MobilePattern.OBSERVABILITY_WIRED: self._check_observability,
            MobilePattern.CI_CD_PIPELINE: self._check_ci_cd,
        }
        results: list[PatternResult] = []
        for pattern in self._all_patterns:
            checker = check_map.get(pattern)
            if checker is not None:
                results.append(checker())
        return results

    def audit_summary(self) -> dict[str, Any]:
        """Return a summary dict of the audit results."""
        results = self.audit()
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed
        critical = sum(1 for r in results if not r.passed and r.severity == PatternSeverity.CRITICAL)
        warnings = sum(1 for r in results if not r.passed and r.severity == PatternSeverity.WARNING)
        score = round((passed / total * 100) if total > 0 else 0.0, 1)
        return {
            "platform": self._platform.value,
            "total": total,
            "passed": passed,
            "failed": failed,
            "critical": critical,
            "warnings": warnings,
            "score": score,
            "results": [r.to_dict() for r in results],
        }

    # -- Individual pattern checks (each <30 lines) --

    def _check_feature_first(self) -> PatternResult:
        """Check for feature-first directory structure."""
        if self._platform == MobilePlatform.FLUTTER:
            ok = _has_dir(self._root, "lib", "features")
        else:
            ok = _has_dir(self._root, "src", "features") or _has_dir(self._root, "app")
        return PatternResult(
            MobilePattern.FEATURE_FIRST_ARCHITECTURE,
            ok,
            PatternSeverity.CRITICAL if not ok else PatternSeverity.INFO,
            "Feature-first structure (lib/features/ or src/features/)" if ok
            else "Missing feature-first structure. Create lib/features/<feature>/{data,domain,presentation}",
            "lib/features/" if self._platform == MobilePlatform.FLUTTER else "src/features/",
        )

    def _check_clean_layering(self) -> PatternResult:
        """Check for clean architecture layers (domain/data/presentation)."""
        if self._platform == MobilePlatform.FLUTTER:
            base = self._root / "lib" / "features"
        else:
            base = self._root / "src" / "features"
        if not base.is_dir():
            return PatternResult(
                MobilePattern.CLEAN_LAYERING, False, PatternSeverity.CRITICAL,
                "No features directory found", str(base),
            )
        dirs = [d for d in base.iterdir() if d.is_dir()]
        has_layers = any(
            (f / "domain").is_dir() or (f / "data").is_dir() or (f / "presentation").is_dir()
            or (f / "components").is_dir() or (f / "services").is_dir()
            for f in dirs
        )
        return PatternResult(
            MobilePattern.CLEAN_LAYERING, has_layers, PatternSeverity.CRITICAL if not has_layers else PatternSeverity.INFO,
            "Clean layers (domain/data/presentation or components/services) found" if has_layers
            else "Features lack clean layer subdirectories",
            str(base),
        )

    def _check_backend_isolation(self) -> PatternResult:
        """Check that backend SDK is isolated to data layer."""
        if self._platform == MobilePlatform.FLUTTER:
            domain_dir = self._root / "lib" / "features"
            if not domain_dir.is_dir():
                return PatternResult(MobilePattern.BACKEND_ISOLATION, False, PatternSeverity.WARNING,
                                     "No features dir to check backend isolation", "lib/features/")
            violations: list[str] = []
            for f in domain_dir.rglob("*.dart"):
                parts = f.parts
                if "domain" in parts or "presentation" in parts:
                    try:
                        text = f.read_text(encoding="utf-8", errors="ignore")
                    except OSError:
                        continue
                    if "package:firebase" in text or "package:supabase" in text:
                        violations.append(str(f.relative_to(self._root)))
            ok = len(violations) == 0
            return PatternResult(
                MobilePattern.BACKEND_ISOLATION, ok, PatternSeverity.CRITICAL if not ok else PatternSeverity.INFO,
                "Backend SDK isolated to data/ layer" if ok
                else f"Backend SDK found in domain/presentation: {violations[:3]}",
                "lib/features/",
            )
        # RN: check that @supabase / firebase imports are not in components/ or hooks/ (only services/)
        features_dir = self._root / "src" / "features"
        if not features_dir.is_dir():
            return PatternResult(MobilePattern.BACKEND_ISOLATION, True, PatternSeverity.INFO,
                                 "No src/features/ dir to check backend isolation (RN)", None)
        rn_violations: list[str] = []
        for f in features_dir.rglob("*.ts"):
            parts = f.parts
            if "components" in parts or "hooks" in parts:
                try:
                    text = f.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                if "@supabase/supabase-js" in text or "firebase/auth" in text or "firebase/firestore" in text:
                    rn_violations.append(str(f.relative_to(self._root)))
        ok_rn = len(rn_violations) == 0
        return PatternResult(
            MobilePattern.BACKEND_ISOLATION, ok_rn, PatternSeverity.CRITICAL if not ok_rn else PatternSeverity.INFO,
            "Backend SDK isolated to services/ layer (RN)" if ok_rn
            else f"Backend SDK found in components/hooks: {rn_violations[:3]}",
            "src/features/",
        )

    def _check_router_refresh(self) -> PatternResult:
        """Check for Router Refresh Pattern (Flutter-specific)."""
        ok = _rglob_exists(self._root, ["lib"], "*router*.dart") and (
            _dir_contains_recursive(self._root, ["lib"], "refreshListenable")
            or _dir_contains_recursive(self._root, ["lib"], "RouterRefreshNotifier")
            or _dir_contains_recursive(self._root, ["lib"], "ChangeNotifier")
        )
        return PatternResult(
            MobilePattern.ROUTER_REFRESH_PATTERN, ok, PatternSeverity.WARNING if not ok else PatternSeverity.INFO,
            "Router Refresh Pattern detected" if ok
            else "Missing Router Refresh Pattern (use _RouterRefreshNotifier + ref.listen)",
            "lib/core/router/",
        )

    def _check_freezed_failure(self) -> PatternResult:
        """Check for Freezed Failure union type (Flutter-specific)."""
        ok = _file_contains(self._root, ["pubspec.yaml"], "freezed") and (
            _rglob_exists(self._root, ["lib"], "failure*.dart")
            and _dir_contains_recursive(self._root, ["lib"], "@freezed")
        )
        return PatternResult(
            MobilePattern.FREEZED_FAILURE_UNION, ok, PatternSeverity.WARNING if not ok else PatternSeverity.INFO,
            "Freezed Failure union type found" if ok
            else "Missing Freezed Failure union (network/cache/auth/server/permission/unknown)",
            "lib/core/errors/",
        )

    def _check_type_safe_routing(self) -> PatternResult:
        """Check for type-safe routing (go_router_builder or typed routes)."""
        if self._platform == MobilePlatform.FLUTTER:
            ok = _file_contains(self._root, ["pubspec.yaml"], "go_router_builder") and (
                _dir_contains_recursive(self._root, ["lib"], "TypedGoRoute")
                or _dir_contains_recursive(self._root, ["lib"], "TypedStatefulShellRoute")
            )
        else:
            ok = _file_contains(self._root, ["app.json"], "typedRoutes")
        return PatternResult(
            MobilePattern.TYPE_SAFE_ROUTING, ok, PatternSeverity.WARNING if not ok else PatternSeverity.INFO,
            "Type-safe routing enabled" if ok
            else "Missing type-safe routing (go_router_builder or typedRoutes)",
            "lib/core/router/" if self._platform == MobilePlatform.FLUTTER else "app.json",
        )

    def _check_usecase_pattern(self) -> PatternResult:
        """Check for UseCase pattern (Flutter-specific)."""
        ok = _rglob_exists(self._root, ["lib"], "use_case*.dart") or _rglob_exists(self._root, ["lib"], "usecase*.dart")
        return PatternResult(
            MobilePattern.USECASE_PATTERN, ok, PatternSeverity.INFO,
            "UseCase pattern detected" if ok
            else "No UseCase classes found (optional but recommended for DDD)",
            "lib/features/*/domain/usecases/",
        )

    def _check_offline_first(self) -> PatternResult:
        """Check for offline-first persistence setup."""
        if self._platform == MobilePlatform.FLUTTER:
            ok = _file_contains(self._root, ["pubspec.yaml"], "drift") or _file_contains(self._root, ["pubspec.yaml"], "isar")
            hint = "pubspec.yaml (drift/isar)"
        else:
            ok = _file_contains(self._root, ["package.json"], "react-native-mmkv") or _file_contains(self._root, ["package.json"], "watermelondb")
            hint = "package.json (mmkv/watermelondb)"
        return PatternResult(
            MobilePattern.OFFLINE_FIRST_SYNC, ok, PatternSeverity.WARNING if not ok else PatternSeverity.INFO,
            "Offline-first persistence detected" if ok
            else "Missing offline-first DB (drift/isar or MMKV/WatermelonDB)",
            hint,
        )

    def _check_secure_storage(self) -> PatternResult:
        """Check for secure token storage."""
        if self._platform == MobilePlatform.FLUTTER:
            ok = _file_contains(self._root, ["pubspec.yaml"], "flutter_secure_storage")
            hint = "pubspec.yaml (flutter_secure_storage)"
        else:
            ok = _file_contains(self._root, ["package.json"], "expo-secure-store")
            hint = "package.json (expo-secure-store)"
        return PatternResult(
            MobilePattern.SECURE_TOKEN_STORAGE, ok, PatternSeverity.CRITICAL if not ok else PatternSeverity.INFO,
            "Secure token storage detected" if ok
            else "CRITICAL: No secure storage for tokens (flutter_secure_storage or expo-secure-store)",
            hint,
        )

    def _check_ordered_logout(self) -> PatternResult:
        """Check for ordered logout cleanup pattern (RN-specific)."""
        if self._platform != MobilePlatform.REACT_NATIVE:
            return PatternResult(
                MobilePattern.ORDERED_LOGOUT_CLEANUP, True, PatternSeverity.INFO,
                "Ordered logout check skipped (RN-only)", None,
            )
        src_dirs = ["src", "app", "lib"]
        ok = any(
            _dir_contains_recursive(self._root, [d], "cancelQueries", ".ts")
            and _dir_contains_recursive(self._root, [d], "queryClient.clear", ".ts")
            for d in src_dirs if _has_dir(self._root, d)
        )
        return PatternResult(
            MobilePattern.ORDERED_LOGOUT_CLEANUP, ok, PatternSeverity.WARNING if not ok else PatternSeverity.INFO,
            "Ordered logout cleanup detected" if ok
            else "Missing ordered logout (cancelQueries -> reset analytics -> clear cache -> signOut)",
            "src/features/auth/",
        )

    def _check_query_cache_buster(self) -> PatternResult:
        """Check for query cache buster pattern (RN-specific)."""
        if self._platform != MobilePlatform.REACT_NATIVE:
            return PatternResult(
                MobilePattern.QUERY_CACHE_BUSTER, True, PatternSeverity.INFO,
                "Query cache buster check skipped (RN-only)", None,
            )
        src_dirs = ["src", "app", "lib"]
        ok = any(
            _dir_contains_recursive(self._root, [d], "cacheBuster", ".ts")
            or _dir_contains_recursive(self._root, [d], "cache_buster", ".ts")
            for d in src_dirs if _has_dir(self._root, d)
        )
        return PatternResult(
            MobilePattern.QUERY_CACHE_BUSTER, ok, PatternSeverity.INFO,
            "Query cache buster detected" if ok
            else "No query cache buster (prevents cross-user cache leaks on shared devices)",
            "src/providers/",
        )

    def _check_design_tokens(self) -> PatternResult:
        """Check for centralized design token system."""
        if self._platform == MobilePlatform.FLUTTER:
            ok = _rglob_exists(self._root, ["lib"], "theme*.dart") or _has_dir(self._root, "lib", "design_system")
        else:
            ok = _has_dir(self._root, "src", "theme")
        return PatternResult(
            MobilePattern.DESIGN_TOKEN_SYSTEM, ok, PatternSeverity.WARNING if not ok else PatternSeverity.INFO,
            "Design token system found" if ok
            else "Missing centralized design tokens (theme/ with colors, spacing, radius, typography)",
            "lib/design_system/" if self._platform == MobilePlatform.FLUTTER else "src/theme/",
        )

    def _check_i18n_rtl(self) -> PatternResult:
        """Check for i18n with RTL support."""
        if self._platform == MobilePlatform.FLUTTER:
            ok = _file_contains(self._root, ["pubspec.yaml"], "flutter_localizations") or _file_contains(self._root, ["pubspec.yaml"], "slang")
            hint = "pubspec.yaml (flutter_localizations or slang)"
        else:
            ok = _file_contains(self._root, ["package.json"], "i18next") or _file_contains(self._root, ["package.json"], "react-i18next")
            hint = "package.json (i18next)"
        return PatternResult(
            MobilePattern.I18N_WITH_RTL, ok, PatternSeverity.WARNING if not ok else PatternSeverity.INFO,
            "i18n setup detected" if ok
            else "Missing i18n (flutter_localizations/slang or i18next) — never hardcode user-facing strings",
            hint,
        )

    def _check_two_tier_testing(self) -> PatternResult:
        """Check for two-tier testing setup (unit + integration/E2E)."""
        if self._platform == MobilePlatform.FLUTTER:
            has_unit = _has_dir(self._root, "test")
            has_e2e = _has_dir(self._root, "integration_test")
        else:
            has_unit = (
                _has_dir(self._root, "__tests__")
                or bool(list(self._root.rglob("*.test.ts")))
                or bool(list(self._root.rglob("*.test.tsx")))
                or bool(list(self._root.rglob("*.spec.ts")))
            )
            has_e2e = _has_dir(self._root, ".maestro") or _file_contains(self._root, ["package.json"], "detox")
        ok = has_unit and has_e2e
        return PatternResult(
            MobilePattern.TWO_TIER_TESTING, ok, PatternSeverity.CRITICAL if not ok else PatternSeverity.INFO,
            f"Two-tier testing: unit={has_unit}, E2E={has_e2e}" if ok
            else f"Missing testing tier: unit={has_unit}, E2E={has_e2e}",
            "test/ + integration_test/" if self._platform == MobilePlatform.FLUTTER else "__tests__/ + .maestro/",
        )

    def _check_ai_instructions(self) -> PatternResult:
        """Check for AI instruction files (AGENTS.md, .cursorrules)."""
        ok = _has_file(self._root, "AGENTS.md") or _has_file(self._root, "CLAUDE.md") or _has_file(self._root, ".cursorrules")
        return PatternResult(
            MobilePattern.AI_INSTRUCTION_FILES, ok, PatternSeverity.INFO,
            "AI instruction files found" if ok
            else "No AI instruction files (AGENTS.md, .cursorrules) — recommended for AI-assisted dev",
            "AGENTS.md",
        )

    def _check_component_library(self) -> PatternResult:
        """Check for shared component library."""
        if self._platform == MobilePlatform.FLUTTER:
            ok = _has_dir(self._root, "lib", "shared", "widgets") or _rglob_exists(self._root, ["lib"], "widgets")
        else:
            ok = _has_dir(self._root, "src", "common", "components")
        return PatternResult(
            MobilePattern.COMPONENT_LIBRARY, ok, PatternSeverity.INFO,
            "Shared component library found" if ok
            else "No shared component library (src/common/components/ or lib/shared/widgets/)",
            "lib/shared/widgets/" if self._platform == MobilePlatform.FLUTTER else "src/common/components/",
        )

    def _check_observability(self) -> PatternResult:
        """Check for crash reporting + analytics."""
        if self._platform == MobilePlatform.FLUTTER:
            has_crash = _file_contains(self._root, ["pubspec.yaml"], "sentry") or _file_contains(self._root, ["pubspec.yaml"], "crashlytics")
            has_analytics = _file_contains(self._root, ["pubspec.yaml"], "posthog") or _file_contains(self._root, ["pubspec.yaml"], "analytics")
        else:
            has_crash = _file_contains(self._root, ["package.json"], "sentry")
            has_analytics = _file_contains(self._root, ["package.json"], "posthog") or _file_contains(self._root, ["package.json"], "mixpanel") or _file_contains(self._root, ["package.json"], "amplitude")
        ok = has_crash and has_analytics
        return PatternResult(
            MobilePattern.OBSERVABILITY_WIRED, ok, PatternSeverity.WARNING if not ok else PatternSeverity.INFO,
            f"Observability: crash={has_crash}, analytics={has_analytics}" if ok
            else f"Missing observability: crash={has_crash}, analytics={has_analytics} (Sentry + PostHog recommended)",
            "pubspec.yaml" if self._platform == MobilePlatform.FLUTTER else "package.json",
        )

    def _check_ci_cd(self) -> PatternResult:
        """Check for CI/CD pipeline configuration."""
        ok = (
            _has_dir(self._root, ".github", "workflows")
            or _has_file(self._root, "eas.json")
            or _has_file(self._root, "codemagic.yaml")
            or _has_file(self._root, "bitrise.yml")
            or _has_file(self._root, "Fastfile")
            or _has_file(self._root, "fastlane", "Fastfile")
            or _has_dir(self._root, "fastlane")
            or _has_file(self._root, "ios", "fastlane", "Fastfile")
            or _has_file(self._root, "android", "fastlane", "Fastfile")
        )
        return PatternResult(
            MobilePattern.CI_CD_PIPELINE, ok, PatternSeverity.WARNING if not ok else PatternSeverity.INFO,
            "CI/CD pipeline detected" if ok
            else "No CI/CD config (.github/workflows, eas.json, codemagic.yaml, fastlane/Fastfile)",
            ".github/workflows/ or eas.json",
        )
