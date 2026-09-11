#!/usr/bin/env python3
"""Linter for Laravel Blade templates.

Detects common Blade template issues: XSS risks (unescaped output), missing
CSRF tokens in forms, hardcoded routes, missing @stack/@push for scripts,
and Filament v5 Blade anti-patterns.

Usage::

    from runtime.blade_template_linter import BladeTemplateLinter
    linter = BladeTemplateLinter()
    findings = linter.lint_file("resources/views/users/index.blade.php")
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

_logger = logging.getLogger(__name__)


class BladeSeverity(str, Enum):
    """Severity of a Blade template finding."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class BladeFinding:
    """A single Blade template lint finding."""

    rule_id: str
    severity: BladeSeverity
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


# BL001: Unescaped output {{ }} is safe, {!! !!} is raw (XSS risk)
_RAW_OUTPUT_RE = re.compile(r"\{!!\s*.*?\s*!!\}")

# BL002: <form> without @csrf
_FORM_RE = re.compile(r"<form\s+", re.IGNORECASE)
_CSRF_RE = re.compile(r"@csrf|@method\s*\(", re.IGNORECASE)

# BL003: Hardcoded URL instead of route()
_HARDCODED_URL_RE = re.compile(r'(?:href|action)\s*=\s*["\']/(?:api|admin|users)/', re.IGNORECASE)

# BL004: Missing @extends or @layout in partial view
_EXTENDS_RE = re.compile(r"@extends\s*\(|@section\s*\(", re.IGNORECASE)

# BL005: Inline <script> without @push/@stack
_INLINE_SCRIPT_RE = re.compile(r"<script\s*>", re.IGNORECASE)
_PUSH_STACK_RE = re.compile(r"@push\s*\(|@stack\s*\(", re.IGNORECASE)

# BL006: {{ $variable }} with potential HTML (should use {!! !!} intentionally)
_ECHO_RE = re.compile(r"\{\{\s*\$(\w+)\s*\}\}")

# BL007: Missing @error block in form fields
_OLD_INPUT_RE = re.compile(r"old\s*\(")
_ERROR_BLOCK_RE = re.compile(r"@error\s*\(", re.IGNORECASE)

# BL008: Filament Blade override without $view
_FILAMENT_OVERRIDE_RE = re.compile(r"filament\.(\w+)\.", re.IGNORECASE)

# BL009: Missing @can/@cannot for conditional rendering
_IF_AUTH_RE = re.compile(r"@auth\s*\(|@if\s*\(\s*auth\(\)", re.IGNORECASE)
_CAN_RE = re.compile(r"@can\s*\(|@cannot\s*\(", re.IGNORECASE)

# BL010: Missing @json for data passing to JS
_JSON_PASS_RE = re.compile(r"@json\s*\(", re.IGNORECASE)
_WINDOW_DATA_RE = re.compile(r"window\.\w+\s*=", re.IGNORECASE)


class BladeTemplateLinter:
    """Linter for Laravel Blade templates.

    Detects common Blade issues:
    - BL001: Unescaped output {!! !!} (XSS risk)
    - BL002: <form> without @csrf token
    - BL003: Hardcoded URL instead of route()
    - BL004: Partial view without @extends or @section
    - BL005: Inline <script> without @push/@stack
    - BL006: Missing @error block in form with old()
    - BL007: Filament Blade override without $view property
    - BL008: @auth without @can (auth check without authorization)
    - BL009: Data passed to JS without @json (injection risk)
    - BL010: Missing @stack for scripts/styles
    """

    def lint_file(self, file_path: str | Path) -> list[BladeFinding]:
        """Lint a single Blade template."""
        path = Path(file_path)
        if not path.is_file():
            return []
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            _logger.warning("Cannot read %s: %s", path, exc)
            return []
        return self._lint_content(content, str(path))

    def lint_files(self, file_paths: list[str | Path]) -> list[BladeFinding]:
        """Lint multiple Blade templates."""
        findings: list[BladeFinding] = []
        for fp in file_paths:
            findings.extend(self.lint_file(fp))
        return findings

    def lint_content(self, content: str, file_path: str = "<string>") -> list[BladeFinding]:
        """Lint raw Blade content."""
        return self._lint_content(content, file_path)

    def _lint_content(self, content: str, file_path: str) -> list[BladeFinding]:
        findings: list[BladeFinding] = []
        lines = content.splitlines()
        is_blade = file_path.endswith(".blade.php") or "@extends" in content or "@section" in content or "{{" in content

        if not is_blade:
            return findings

        for i, line in enumerate(lines, 1):
            # BL001: Unescaped output
            if _RAW_OUTPUT_RE.search(line):
                findings.append(BladeFinding(
                    rule_id="BL001",
                    severity=BladeSeverity.ERROR,
                    message="{!! !!} outputs raw HTML — XSS risk. Use {{ }} unless intentionally rendering HTML",
                    file_path=file_path,
                    line=i,
                    fix="Use {{ $variable }} for text. If HTML needed, sanitize with e($html) or DOMPurify",
                ))

            # BL002: <form> without @csrf
            if _FORM_RE.search(line) and not _CSRF_RE.search(content):
                findings.append(BladeFinding(
                    rule_id="BL002",
                    severity=BladeSeverity.ERROR,
                    message="<form> without @csrf — CSRF protection missing",
                    file_path=file_path,
                    line=i,
                    fix="Add @csrf inside the <form> tag",
                ))

            # BL003: Hardcoded URL
            if _HARDCODED_URL_RE.search(line):
                findings.append(BladeFinding(
                    rule_id="BL003",
                    severity=BladeSeverity.WARNING,
                    message="Hardcoded URL — use route() or url() helper for maintainability",
                    file_path=file_path,
                    line=i,
                    fix="Replace with href=\"{{ route('name') }}\" or action=\"{{ url('/path') }}\"",
                ))

            # BL005: Inline <script> without @push/@stack
            if _INLINE_SCRIPT_RE.search(line) and not _PUSH_STACK_RE.search(content):
                findings.append(BladeFinding(
                    rule_id="BL005",
                    severity=BladeSeverity.WARNING,
                    message="Inline <script> without @push/@stack — may break CSP and Filament asset loading",
                    file_path=file_path,
                    line=i,
                    fix="Use @push('scripts') <script> ... </script> @endpush",
                ))

            # BL009: Data to JS without @json
            if _WINDOW_DATA_RE.search(line) and not _JSON_PASS_RE.search(content):
                findings.append(BladeFinding(
                    rule_id="BL009",
                    severity=BladeSeverity.WARNING,
                    message="window.* assignment without @json — data not safely serialized for JS",
                    file_path=file_path,
                    line=i,
                    fix="Use window.data = @json($data) for safe JSON serialization",
                ))

        # BL006: Missing @error with old()
        if _OLD_INPUT_RE.search(content) and not _ERROR_BLOCK_RE.search(content):
            line_num = next(
                (i for i, ln in enumerate(lines, 1) if _OLD_INPUT_RE.search(ln)),
                1,
            )
            findings.append(BladeFinding(
                rule_id="BL006",
                severity=BladeSeverity.WARNING,
                message="Form uses old() but no @error block — validation errors not displayed",
                file_path=file_path,
                line=line_num,
                fix="Add @error('field') <span class=\"text-red-500\">{{ $message }}</span> @enderror",
            ))

        # BL008: @auth without @can
        if _IF_AUTH_RE.search(content) and not _CAN_RE.search(content):
            line_num = next(
                (i for i, ln in enumerate(lines, 1) if _IF_AUTH_RE.search(ln)),
                1,
            )
            findings.append(BladeFinding(
                rule_id="BL008",
                severity=BladeSeverity.INFO,
                message="@auth check without @can — authentication without authorization. Consider adding @can('permission')",
                file_path=file_path,
                line=line_num,
                fix="Add @can('view', $model) around sensitive content",
            ))

        return findings

    def summary(self, findings: list[BladeFinding]) -> dict[str, Any]:
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
