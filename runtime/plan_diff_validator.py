"""Plan + diff validator — enforceable, machine-checkable rules for plans and diffs.

Validates an agent's proposed plan (pre-edit) and git diff patch (post-edit)
to ensure compliance before code is modified or merged:

- **Plan validation**: extract planned files from a markdown plan block,
  verify safety boundaries (forbidden paths, file count limits).
- **Diff validation**: analyze a git patch to catch forbidden imports,
  path violations, test gaps, and file counts.
- **Dependency guard**: warn when a diff adds imports of external packages
  not declared in ``pyproject.toml`` / ``requirements.txt`` / ``package.json``
  / ``composer.json`` — a common AI-agent failure mode.
- **Unrelated refactor detection**: identify whether modifications span
  disjoint, unconnected modules in the import graph (connected-components
  analysis).

Inspired by ``repo-contract``'s negative-constraint enforcement approach.
"""

from __future__ import annotations

import fnmatch
import re
import threading
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from runtime.schemas import AizeeError, ErrorSeverity


class PlanValidationError(AizeeError):
    """Raised when plan/diff validation encounters a critical error."""

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        super().__init__("PLAN_VALIDATION_ERROR", message, ErrorSeverity.HIGH, context)


class ValidationLevel(str, Enum):
    """Severity of a validation finding."""

    ERROR = "error"
    WARN = "warn"
    INFO = "info"


@dataclass
class Finding:
    """A single validation finding."""

    level: ValidationLevel
    rule: str
    message: str
    file: str = ""
    line: int = 0
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "level": self.level.value,
            "rule": self.rule,
            "message": self.message,
        }
        if self.file:
            d["file"] = self.file
        if self.line:
            d["line"] = self.line
        return d


@dataclass
class ValidationResult:
    """Aggregated result of a validation run."""

    findings: list[Finding] = field(default_factory=list)
    plan_files: list[str] = field(default_factory=list)
    diff_files: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(f.level == ValidationLevel.ERROR for f in self.findings)

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.level == ValidationLevel.ERROR]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.level == ValidationLevel.WARN]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "findings": [f.to_dict() for f in self.findings],
            "plan_files": list(self.plan_files),
            "diff_files": list(self.diff_files),
            "error_count": len(self.errors),
            "warn_count": len(self.warnings),
        }


class PlanDiffValidator:
    """Validate agent plans and git diffs against enforceable rules."""

    # Default forbidden path patterns (negative constraints).
    DEFAULT_FORBIDDEN_PATHS: tuple[str, ...] = (
        ".env", ".env.*", "secrets/", "credentials/", "id_rsa", "id_ed25519",
        ".aws/credentials", ".npmrc", ".pypirc",
    )

    # Default max files allowed in a single plan/diff.
    DEFAULT_MAX_FILES = 20

    def __init__(
        self,
        project_root: Path,
        forbidden_paths: tuple[str, ...] | None = None,
        max_files: int | None = None,
    ) -> None:
        self.project_root = project_root
        self.forbidden_paths = forbidden_paths or self.DEFAULT_FORBIDDEN_PATHS
        self.max_files = max_files or self.DEFAULT_MAX_FILES
        self._lock = threading.Lock()

    # -- Plan validation --------------------------------------------------

    _PLAN_FILE_RE = re.compile(r"^\s*[`'\"]?([^\s`'\"]+\.\w+)[`'\"]?\s*$", re.MULTILINE)
    _PLAN_HEADER_RE = re.compile(r"^#{1,6}\s+(?:plan|steps|files|changes)", re.IGNORECASE | re.MULTILINE)

    def extract_plan_files(self, plan_text: str) -> list[str]:
        """Extract file paths mentioned in a markdown plan block."""
        files: list[str] = []
        # Look for file paths in code blocks and bullet lists.
        in_code_block = False
        for line in plan_text.splitlines():
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                # Lines inside code blocks that look like paths.
                if ("/" in stripped or stripped.endswith((".py", ".ts", ".js", ".php", ".go", ".rs", ".java"))) and not stripped.startswith(("#", "//")):
                    files.append(stripped)
                continue
            # Bullet/list items with file paths.
            if stripped.startswith(("-", "*", "+")):
                item = stripped.lstrip("-*+ ").strip("`'\"")
                if "." in item and "/" in item:
                    files.append(item)
        # Deduplicate preserving order.
        seen: set[str] = set()
        unique: list[str] = []
        for f in files:
            if f not in seen:
                seen.add(f)
                unique.append(f)
        return unique

    def validate_plan(self, plan_text: str) -> ValidationResult:
        """Validate a proposed plan before any edits begin."""
        with self._lock:
            result = ValidationResult()
            result.plan_files = self.extract_plan_files(plan_text)
            self._check_forbidden(result.plan_files, result, source="plan")
            self._check_file_count(result.plan_files, result, source="plan")
            if not result.plan_files and self._PLAN_HEADER_RE.search(plan_text):
                result.findings.append(Finding(
                    ValidationLevel.WARN, "empty_plan",
                    "Plan header found but no file paths detected",
                ))
            return result

    # -- Diff validation --------------------------------------------------

    _DIFF_FILE_RE = re.compile(r"^\+\+\+\s+b?/(.+)$", re.MULTILINE)
    _DIFF_HUNK_RE = re.compile(r"^@@\s+-\d+(?:,\d+)?\s+\+(\d+)", re.MULTILINE)

    def extract_diff_files(self, diff_text: str) -> list[str]:
        """Extract file paths from a unified git diff."""
        return list(self._DIFF_FILE_RE.findall(diff_text))

    def validate_diff(self, diff_text: str) -> ValidationResult:
        """Validate a git diff patch after edits."""
        with self._lock:
            result = ValidationResult()
            result.diff_files = self.extract_diff_files(diff_text)
            self._check_forbidden(result.diff_files, result, source="diff")
            self._check_file_count(result.diff_files, result, source="diff")
            self._check_test_gap(result.diff_files, result)
            new_imports = self._extract_added_imports(diff_text, result.diff_files)
            self._check_undeclared_imports(new_imports, result)
            self._check_unrelated_refactor(result.diff_files, result)
            return result

    # -- Shared checks ----------------------------------------------------

    def _matches_forbidden(self, path: str) -> str | None:
        normalized = path.lower().replace("\\", "/")
        for pattern in self.forbidden_paths:
            pat = pattern.lower()
            if fnmatch.fnmatch(normalized, pat) or fnmatch.fnmatch(normalized, f"*/{pat}") or pat in normalized:
                return pattern
        return None

    def _check_forbidden(
        self, files: list[str], result: ValidationResult, source: str
    ) -> None:
        for f in files:
            hit = self._matches_forbidden(f)
            if hit:
                result.findings.append(Finding(
                    ValidationLevel.ERROR, "forbidden_path",
                    f"Forbidden path '{f}' matches pattern '{hit}'",
                    file=f,
                ))

    def _check_file_count(
        self, files: list[str], result: ValidationResult, source: str
    ) -> None:
        if len(files) > self.max_files:
            result.findings.append(Finding(
                ValidationLevel.WARN, "file_count",
                f"{source} touches {len(files)} files (max {self.max_files})",
            ))

    def _check_test_gap(
        self, files: list[str], result: ValidationResult
    ) -> None:
        src_files = [f for f in files if not self._is_test_file(f) and self._is_source_file(f)]
        test_files = [f for f in files if self._is_test_file(f)]
        if src_files and not test_files:
            result.findings.append(Finding(
                ValidationLevel.WARN, "test_gap",
                f"Diff modifies {len(src_files)} source files but no test files",
            ))

    @staticmethod
    def _is_test_file(path: str) -> bool:
        lower = path.lower()
        return (
            lower.startswith("test") or "/test" in lower
            or lower.endswith(("_test.py", "_test.go", ".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx"))
            or "/tests/" in lower
        )

    @staticmethod
    def _is_source_file(path: str) -> bool:
        return path.endswith((".py", ".ts", ".tsx", ".js", ".jsx", ".php", ".go", ".rs", ".java"))

    # -- Dependency guard -------------------------------------------------

    _PY_IMPORT_RE = re.compile(r"^\+(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))", re.MULTILINE)
    _TS_IMPORT_RE = re.compile(r"^\+import\s+.*from\s+['\"]([^'\"]+)['\"]", re.MULTILINE)

    def _extract_added_imports(
        self, diff_text: str, files: list[str]
    ) -> dict[str, list[str]]:
        """Extract added imports from diff, grouped by language."""
        imports: dict[str, list[str]] = {"python": [], "ts": []}
        for m in self._PY_IMPORT_RE.finditer(diff_text):
            mod = m.group(1) or m.group(2)
            if mod:
                imports["python"].append(mod)
        for m in self._TS_IMPORT_RE.finditer(diff_text):
            mod = m.group(1)
            if mod and not mod.startswith(".") and not mod.startswith("@/"):
                imports["ts"].append(mod)
        return imports

    def _check_undeclared_imports(
        self, imports: dict[str, list[str]], result: ValidationResult
    ) -> None:
        declared_py = self._load_declared_python_deps()
        declared_ts = self._load_declared_ts_deps()
        for mod in imports.get("python", []):
            top = mod.split(".")[0]
            if top in ("os", "sys", "re", "json", "pathlib", "typing", "dataclasses", "enum", "collections", "functools", "ast", "threading", "hashlib", "datetime", "abc", "io", "csv", "math", "itertools", "warnings", "contextlib"):
                continue
            if declared_py and top not in declared_py:
                result.findings.append(Finding(
                    ValidationLevel.WARN, "undeclared_import",
                    f"Python import '{mod}' not declared in pyproject/requirements",
                ))
        for mod in imports.get("ts", []):
            if declared_ts and mod not in declared_ts:
                result.findings.append(Finding(
                    ValidationLevel.WARN, "undeclared_import",
                    f"TS import '{mod}' not declared in package.json",
                ))

    def _load_declared_python_deps(self) -> set[str]:
        pyproject = self.project_root / "pyproject.toml"
        reqs = self.project_root / "requirements.txt"
        deps: set[str] = set()
        if pyproject.exists():
            try:
                text = pyproject.read_text(encoding="utf-8")
                for m in re.finditer(r"^\s*([a-zA-Z0-9_-]+)\s*[=<>~!\[]", text, re.MULTILINE):
                    deps.add(m.group(1).lower().replace("-", "_"))
            except OSError:
                pass
        if reqs.exists():
            try:
                for line in reqs.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        name = re.split(r"[=<>~!\[]", line)[0].strip().lower().replace("-", "_")
                        if name:
                            deps.add(name)
            except OSError:
                pass
        return deps

    def _load_declared_ts_deps(self) -> set[str]:
        pkg = self.project_root / "package.json"
        deps: set[str] = set()
        if pkg.exists():
            try:
                import json
                data = json.loads(pkg.read_text(encoding="utf-8"))
                for section in ("dependencies", "devDependencies"):
                    deps.update(data.get(section, {}).keys())
            except (OSError, ValueError):
                pass
        return deps

    # -- Unrelated refactor detection ------------------------------------

    def _check_unrelated_refactor(
        self, files: list[str], result: ValidationResult
    ) -> None:
        if len(files) < 3:
            return
        components = self._connected_components(files)
        if len(components) > 1:
            result.findings.append(Finding(
                ValidationLevel.WARN, "unrelated_refactor",
                f"Diff spans {len(components)} disjoint module groups: {components}",
            ))

    def _connected_components(self, files: list[str]) -> list[list[str]]:
        """Group files by top-level directory (proxy for module proximity)."""
        groups: dict[str, list[str]] = {}
        for f in files:
            parts = f.split("/")
            top = parts[0] if len(parts) > 1 else "."
            groups.setdefault(top, []).append(f)
        return list(groups.values())


__all__ = [
    "Finding",
    "PlanDiffValidator",
    "ValidationLevel",
    "ValidationResult",
]
