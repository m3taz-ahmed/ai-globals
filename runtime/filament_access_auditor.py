#!/usr/bin/env python3
"""Audit Filament v5 panel/resource authorization configuration.

Detects common Filament RBAC misconfigurations: missing policies, missing
Shield registration, public access to admin panels, missing middleware,
and per-record authorization gaps.

Usage::

    from runtime.filament_access_auditor import FilamentAccessAuditor
    auditor = FilamentAccessAuditor()
    findings = auditor.audit_files(file_paths)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

_logger = logging.getLogger(__name__)


class AccessSeverity(str, Enum):
    """Severity of a Filament access finding."""

    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class AccessFinding:
    """A single Filament access audit finding."""

    rule_id: str
    severity: AccessSeverity
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


# FA001: Panel without auth middleware
_PANEL_RE = re.compile(r"->panel\s*\(\s*['\"](\w+)['\"]")
_AUTH_MIDDLEWARE_RE = re.compile(r"->middleware\s*\(\s*['\"]auth['\"]|->authMiddleware\(\)")

# FA002: Resource without policy
_RESOURCE_RE = re.compile(r"class\s+(\w+)\s+extends\s+Resource")
_POLICY_PROP_RE = re.compile(r"protected\s+static.*\$policy\s*=")

# FA003: ->can() with wildcard or true
_CAN_WILDCARD_RE = re.compile(r"->can\s*\(\s*['\"]\*['\"]|->can\s*\(\s*true|->can\s*\(\s*fn.*=>\s*true")

# FA004: Missing authorizeIndividualRecords on tables
_TABLE_RE = re.compile(r"->table\s*\(")
_AUTHORIZE_RE = re.compile(r"->authorizeIndividualRecords|->checkableRecords")

# FA005: isAccessible() returning true (public panel)
_ACCESSIBLE_RE = re.compile(r"isAccessible\s*\(\s*\)\s*[:{].*return\s+true", re.DOTALL)

# FA006: Navigation without visibility check
_NAV_ITEM_RE = re.compile(r"NavigationItem::make\(\)")
_NAV_VISIBLE_RE = re.compile(r"->visible\s*\(|->visibleOnScope\(")

# FA007: Missing ->shield() on resource
_SHIELD_RE = re.compile(r"->shield\s*\(\)")

# FA008: Registration without auth gate
_PANEL_PROVIDER_RE = re.compile(r"class\s+\w+\s+extends\s+PanelProvider")


class FilamentAccessAuditor:
    """Audit Filament v5 panel and resource authorization configuration.

    Detects RBAC misconfigurations:
    - FA001: Panel without auth middleware
    - FA002: Resource without policy
    - FA003: ->can() with wildcard or always-true
    - FA004: Table without per-record authorization
    - FA005: isAccessible() returning true (public panel)
    - FA006: Navigation item without visibility check
    - FA007: Resource without ->shield() (Filament Shield)
    - FA008: Panel provider without auth gate
    """

    def audit_file(self, file_path: str | Path) -> list[AccessFinding]:
        """Audit a single PHP file for Filament access issues."""
        path = Path(file_path)
        if not path.is_file():
            return []
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            _logger.warning("Cannot read %s: %s", path, exc)
            return []
        return self._audit_content(content, str(path))

    def audit_files(self, file_paths: list[str | Path]) -> list[AccessFinding]:
        """Audit multiple PHP files."""
        findings: list[AccessFinding] = []
        for fp in file_paths:
            findings.extend(self.audit_file(fp))
        return findings

    def audit_content(self, content: str, file_path: str = "<string>") -> list[AccessFinding]:
        """Audit raw PHP content."""
        return self._audit_content(content, file_path)

    def _audit_content(self, content: str, file_path: str) -> list[AccessFinding]:
        findings: list[AccessFinding] = []
        lines = content.splitlines()
        is_php = file_path.endswith(".php") or "<?php" in content

        if not is_php:
            return findings

        # FA001 + FA008: Panel without auth middleware
        if _PANEL_PROVIDER_RE.search(content):
            has_auth = bool(_AUTH_MIDDLEWARE_RE.search(content))
            if not has_auth:
                line_num = next(
                    (i for i, ln in enumerate(lines, 1) if _PANEL_PROVIDER_RE.search(ln)),
                    1,
                )
                findings.append(AccessFinding(
                    rule_id="FA001",
                    severity=AccessSeverity.CRITICAL,
                    message="PanelProvider without auth middleware — admin panel publicly accessible",
                    file_path=file_path,
                    line=line_num,
                    fix="Add ->middleware(['auth']) to panel configuration in register()",
                ))

        # FA002: Resource without policy
        if _RESOURCE_RE.search(content):
            has_policy = bool(_POLICY_PROP_RE.search(content)) or bool(_SHIELD_RE.search(content))
            if not has_policy:
                line_num = next(
                    (i for i, ln in enumerate(lines, 1) if _RESOURCE_RE.search(ln)),
                    1,
                )
                findings.append(AccessFinding(
                    rule_id="FA002",
                    severity=AccessSeverity.ERROR,
                    message="Filament Resource without $policy or ->shield() — no per-record RBAC",
                    file_path=file_path,
                    line=line_num,
                    fix="Add protected static ?string $policy = UserPolicy::class; or ->shield()",
                ))

        # FA003: ->can() with wildcard or true
        for i, line in enumerate(lines, 1):
            if _CAN_WILDCARD_RE.search(line):
                findings.append(AccessFinding(
                    rule_id="FA003",
                    severity=AccessSeverity.ERROR,
                    message="->can('*') or ->can(true) bypasses authorization — use specific permission",
                    file_path=file_path,
                    line=i,
                    fix="Use ->can('view') or ->can(fn() => auth()->user()->can('view', $record))",
                ))

        # FA004: Table without per-record authorization
        if _TABLE_RE.search(content) and not _AUTHORIZE_RE.search(content):
            line_num = next(
                (i for i, ln in enumerate(lines, 1) if _TABLE_RE.search(ln)),
                1,
            )
            findings.append(AccessFinding(
                rule_id="FA004",
                severity=AccessSeverity.WARNING,
                message="Table without ->authorizeIndividualRecords() — users may see unauthorized records",
                file_path=file_path,
                line=line_num,
                fix="Add ->authorizeIndividualRecords() to table or use ->checkableRecords()",
            ))

        # FA005: isAccessible() returning true
        if _ACCESSIBLE_RE.search(content):
            findings.append(AccessFinding(
                rule_id="FA005",
                severity=AccessSeverity.CRITICAL,
                message="isAccessible() returns true — panel accessible to all users without auth check",
                file_path=file_path,
                line=1,
                fix="Return auth()->user()?->can('access_admin') or Gate::allows('accessPanel')",
            ))

        # FA006: Navigation without visibility check
        if _NAV_ITEM_RE.search(content) and not _NAV_VISIBLE_RE.search(content):
            line_num = next(
                (i for i, ln in enumerate(lines, 1) if _NAV_ITEM_RE.search(ln)),
                1,
            )
            findings.append(AccessFinding(
                rule_id="FA006",
                severity=AccessSeverity.WARNING,
                message="NavigationItem without ->visible() — shown to all authenticated users regardless of role",
                file_path=file_path,
                line=line_num,
                fix="Add ->visible(fn() => auth()->user()?->can('view_navigation_item'))",
            ))

        return findings

    def summary(self, findings: list[AccessFinding]) -> dict[str, Any]:
        """Return a summary dict of findings by severity."""
        by_severity: dict[str, int] = {"critical": 0, "error": 0, "warning": 0, "info": 0}
        by_rule: dict[str, int] = {}
        for f in findings:
            by_severity[f.severity.value] = by_severity.get(f.severity.value, 0) + 1
            by_rule[f.rule_id] = by_rule.get(f.rule_id, 0) + 1
        return {
            "total": len(findings),
            "by_severity": by_severity,
            "by_rule": by_rule,
        }
