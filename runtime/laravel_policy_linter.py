#!/usr/bin/env python3
"""Static analysis over Laravel policy classes and Filament authorization.

Detects common Laravel/Filament authorization mistakes that can lead to
security gaps: missing policy methods, bypassed gates, $guarded = [],
missing FormRequest validation, raw SQL, and missing Filament Shield
registration.

Usage::

    from runtime.laravel_policy_linter import LaravelPolicyLinter
    linter = LaravelPolicyLinter()
    findings = linter.lint_files(file_paths)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

_logger = logging.getLogger(__name__)


class LaravelLintSeverity(str, Enum):
    """Severity of a Laravel policy lint finding."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class LaravelFinding:
    """A single Laravel policy lint finding."""

    rule_id: str
    severity: LaravelLintSeverity
    message: str
    file_path: str
    line: int
    fix: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "message": self.message,
            "file_path": self.file_path,
            "line": self.line,
            "fix": self.fix,
        }


# LP001: $guarded = [] (mass assignment vulnerability)
_GUARDED_EMPTY_RE = re.compile(r"\$guarded\s*=\s*\[\s*\]")

# LP002: Raw SQL interpolation (SQL injection risk)
_RAW_SQL_RE = re.compile(r"DB::(raw|select|statement)\s*\(\s*['\"].*\$\w+")

# LP003: Missing FormRequest in controller (unvalidated input)
_CONTROLLER_ACTION_RE = re.compile(
    r"public\s+function\s+(\w+)\s*\(\s*Request\s+\$request"
)

# LP004: bypassGate / withoutAuthorization / Gate::any with wildcard
_BYPASS_GATE_RE = re.compile(
    r"Gate::(any|any)\s*\(\s*['\"]\*['\"]|->withoutAuthorization|bypassGate"
)

# LP005: Missing policy method (viewAny, view, create, update, delete, restore, forceDelete)
_POLICY_METHODS = {"viewany", "view", "create", "update", "delete", "restore", "forcedelete"}

# LP006: Filament resource without ->shield() or policy
_FILAMENT_RESOURCE_RE = re.compile(r"class\s+\w+\s+extends\s+Resource")

# LP007: Auth::check() without redirect (auth bypass)
_AUTH_CHECK_RE = re.compile(r"Auth::check\(\)\s*\)\s*\{[^}]*return\s+(true|1|null)")

# LP008: Missing $fillable (relies on $guarded = [])
_NO_FILLABLE_RE = re.compile(r"protected\s+\$fillable\s*=")


class LaravelPolicyLinter:
    """Static analysis over Laravel policy classes and Filament authorization.

    Detects common security gaps in Laravel 13 + Filament v5 applications:
    - LP001: $guarded = [] (mass assignment vulnerability)
    - LP002: Raw SQL interpolation (SQL injection risk)
    - LP003: Missing FormRequest in controller actions
    - LP004: Bypassed authorization gates
    - LP005: Missing policy methods
    - LP006: Filament resource without Shield/policy
    - LP007: Auth::check() returning truthy without proper guard
    - LP008: Model without $fillable
    """

    def lint_file(self, file_path: str | Path) -> list[LaravelFinding]:
        """Lint a single PHP file for Laravel policy issues."""
        path = Path(file_path)
        if not path.is_file():
            return []
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            _logger.warning("Cannot read %s: %s", path, exc)
            return []
        return self._lint_content(content, str(path))

    def lint_files(self, file_paths: list[str | Path]) -> list[LaravelFinding]:
        """Lint multiple PHP files."""
        findings: list[LaravelFinding] = []
        for fp in file_paths:
            findings.extend(self.lint_file(fp))
        return findings

    def lint_content(self, content: str, file_path: str = "<string>") -> list[LaravelFinding]:
        """Lint raw PHP content."""
        return self._lint_content(content, file_path)

    def _lint_content(self, content: str, file_path: str) -> list[LaravelFinding]:
        findings: list[LaravelFinding] = []
        lines = content.splitlines()
        is_php = file_path.endswith(".php") or "<?php" in content

        if not is_php:
            return findings

        for i, line in enumerate(lines, 1):
            # LP001: $guarded = []
            if _GUARDED_EMPTY_RE.search(line):
                findings.append(LaravelFinding(
                    rule_id="LP001",
                    severity=LaravelLintSeverity.ERROR,
                    message="$guarded = [] allows mass assignment of all columns — use $fillable whitelist instead",
                    file_path=file_path,
                    line=i,
                    fix="Replace $guarded = [] with protected $fillable = ['column1', 'column2'];",
                ))

            # LP002: Raw SQL interpolation
            if _RAW_SQL_RE.search(line):
                findings.append(LaravelFinding(
                    rule_id="LP002",
                    severity=LaravelLintSeverity.ERROR,
                    message="Raw SQL with variable interpolation — SQL injection risk. Use parameterized queries",
                    file_path=file_path,
                    line=i,
                    fix="Use DB::select('SELECT * FROM users WHERE id = ?', [$id]) or Eloquent where clauses",
                ))

            # LP003: Missing FormRequest (Request $request in controller)
            if _CONTROLLER_ACTION_RE.search(line):
                findings.append(LaravelFinding(
                    rule_id="LP003",
                    severity=LaravelLintSeverity.WARNING,
                    message="Controller action uses Request instead of FormRequest — input not validated",
                    file_path=file_path,
                    line=i,
                    fix="Create a FormRequest class: php artisan make:request StoreUserRequest",
                ))

            # LP004: Bypassed authorization
            if _BYPASS_GATE_RE.search(line):
                findings.append(LaravelFinding(
                    rule_id="LP004",
                    severity=LaravelLintSeverity.ERROR,
                    message="Authorization bypass detected — Gate::any('*') or withoutAuthorization skips RBAC",
                    file_path=file_path,
                    line=i,
                    fix="Use specific Gate::allows('action', $model) or policy methods",
                ))

            # LP007: Auth::check() returning truthy
            if _AUTH_CHECK_RE.search(line):
                findings.append(LaravelFinding(
                    rule_id="LP007",
                    severity=LaravelLintSeverity.WARNING,
                    message="Auth::check() returning truthy without proper authorization check — use policies",
                    file_path=file_path,
                    line=i,
                    fix="Use Gate::allows('view', $model) or $this->authorize('view', $model)",
                ))

        # LP006: Filament resource without policy reference
        if _FILAMENT_RESOURCE_RE.search(content):
            has_policy = bool(re.search(r"->shield\(\)|protected\s+static.*\$policy|\$model::class", content))
            if not has_policy:
                line_num = next(
                    (i for i, ln in enumerate(lines, 1) if _FILAMENT_RESOURCE_RE.search(ln)),
                    1,
                )
                findings.append(LaravelFinding(
                    rule_id="LP006",
                    severity=LaravelLintSeverity.WARNING,
                    message="Filament Resource without Shield or $policy — RBAC not enforced",
                    file_path=file_path,
                    line=line_num,
                    fix="Add ->shield() to resource or set protected static $policy = UserPolicy::class",
                ))

        # LP008: Model without $fillable (Eloquent model file)
        if "extends Model" in content and not _NO_FILLABLE_RE.search(content) and not _GUARDED_EMPTY_RE.search(content):
            line_num = next(
                (i for i, ln in enumerate(lines, 1) if "extends Model" in ln),
                1,
            )
            findings.append(LaravelFinding(
                rule_id="LP008",
                severity=LaravelLintSeverity.WARNING,
                message="Eloquent Model without $fillable — mass assignment not whitelisted",
                file_path=file_path,
                line=line_num,
                fix="Add protected $fillable = ['column1', 'column2'];",
            ))

        # LP005: Missing policy methods (check policy files)
        if "extends Policy" in content or file_path.endswith("Policy.php"):
            found_methods = {m for m in _POLICY_METHODS if re.search(rf"function\s+{m}\s*\(", content, re.IGNORECASE)}
            missing = _POLICY_METHODS - found_methods
            if missing:
                findings.append(LaravelFinding(
                    rule_id="LP005",
                    severity=LaravelLintSeverity.WARNING,
                    message=f"Policy missing methods: {', '.join(sorted(missing))} — Filament may fail silently",
                    file_path=file_path,
                    line=1,
                    fix=f"Add missing policy methods: {', '.join(sorted(missing))}",
                ))

        return findings

    def summary(self, findings: list[LaravelFinding]) -> dict[str, Any]:
        """Return a summary dict of findings by severity."""
        by_severity: dict[str, int] = {"error": 0, "warning": 0, "info": 0}
        by_rule: dict[str, int] = {}
        for f in findings:
            by_severity[f.severity.value] = by_severity.get(f.severity.value, 0) + 1
            by_rule[f.rule_id] = by_rule.get(f.rule_id, 0) + 1
        return {
            "total": len(findings),
            "by_severity": by_severity,
            "by_rule": by_rule,
        }
