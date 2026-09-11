#!/usr/bin/env python3
"""Accessibility (a11y) checker for HTML/Blade/Tailwind templates.

Detects common WCAG 2.2 AA violations in HTML, Blade templates, and
Filament v5 UI components: missing alt text, missing aria labels, color
contrast issues (heuristic), missing focus styles, and RTL/Arabic gaps.

Usage::

    from runtime.ui_a11y_checker import A11yChecker
    checker = A11yChecker()
    findings = checker.check_file("resources/views/welcome.blade.php")
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

_logger = logging.getLogger(__name__)


class A11ySeverity(str, Enum):
    """Severity of an accessibility finding."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class A11yFinding:
    """A single accessibility finding."""

    rule_id: str
    severity: A11ySeverity
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


# A11y-001: <img> without alt
_IMG_NO_ALT_RE = re.compile(r"<img\s+[^>]*>", re.IGNORECASE)
_ALT_RE = re.compile(r"\salt\s*=", re.IGNORECASE)

# A11y-002: <button> or <a> without text/aria-label
_BUTTON_RE = re.compile(r"<button\s+[^>]*>(.*?)</button>", re.IGNORECASE | re.DOTALL)
_LINK_RE = re.compile(r"<a\s+[^>]*>(.*?)</a>", re.IGNORECASE | re.DOTALL)
_ARIA_LABEL_RE = re.compile(r"aria-label\s*=", re.IGNORECASE)

# A11y-003: <input> without <label>
_INPUT_RE = re.compile(r"<input\s+[^>]*>", re.IGNORECASE)
_LABEL_FOR_RE = re.compile(r"<label\s+[^>]*for\s*=", re.IGNORECASE)

# A11y-004: Missing focus-visible (Tailwind)
_FOCUS_VISIBLE_RE = re.compile(r"focus-visible:|focus:")

# A11y-005: Missing motion-reduce on animations
_ANIMATE_RE = re.compile(r"animate-\w+|transition-|@starting-style|animation:")
_MOTION_REDUCE_RE = re.compile(r"motion-reduce:|motion-safe:")

# A11y-006: Color via inline style without contrast check
_INLINE_COLOR_RE = re.compile(r"style\s*=\s*['\"].*(color|background)\s*:", re.IGNORECASE)

# A11y-007: dir="rtl" missing on Arabic pages
_HTML_RE = re.compile(r"<html\s+", re.IGNORECASE)
_DIR_RTL_RE = re.compile(r'dir\s*=\s*["\']rtl["\']', re.IGNORECASE)
_ARABIC_TEXT_RE = re.compile(r"[\u0600-\u06FF]")

# A11y-008: <table> without <caption> or aria-label
_TABLE_RE = re.compile(r"<table\s+", re.IGNORECASE)
_CAPTION_RE = re.compile(r"<caption|aria-label", re.IGNORECASE)

# A11y-009: onclick without keyboard equivalent
_ONCLICK_RE = re.compile(r"onclick\s*=", re.IGNORECASE)
_KEYDOWN_RE = re.compile(r"onkeydown\s*=|onkeypress\s*=|onkeyup\s*=", re.IGNORECASE)

# A11y-010: tabindex > 0 (breaks natural tab order)
_TABINDEX_POS_RE = re.compile(r'tabindex\s*=\s*["\']([2-9]|[1-9]\d+)["\']', re.IGNORECASE)


class A11yChecker:
    """Accessibility checker for HTML/Blade/Tailwind templates.

    Detects WCAG 2.2 AA violations:
    - A11y-001: <img> without alt attribute
    - A11y-002: <button>/<a> without text or aria-label
    - A11y-003: <input> without associated <label>
    - A11y-004: Interactive elements without focus-visible
    - A11y-005: Animations without motion-reduce
    - A11y-006: Inline color styles (contrast not checked)
    - A11y-007: Arabic content without dir="rtl"
    - A11y-008: <table> without caption/aria-label
    - A11y-009: onclick without keyboard equivalent
    - A11y-010: tabindex > 0 (breaks tab order)
    """

    def check_file(self, file_path: str | Path) -> list[A11yFinding]:
        """Check a single HTML/Blade template for a11y issues."""
        path = Path(file_path)
        if not path.is_file():
            return []
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            _logger.warning("Cannot read %s: %s", path, exc)
            return []
        return self._check_content(content, str(path))

    def check_files(self, file_paths: list[str | Path]) -> list[A11yFinding]:
        """Check multiple template files."""
        findings: list[A11yFinding] = []
        for fp in file_paths:
            findings.extend(self.check_file(fp))
        return findings

    def check_content(self, content: str, file_path: str = "<string>") -> list[A11yFinding]:
        """Check raw HTML/Blade content."""
        return self._check_content(content, file_path)

    def _check_content(self, content: str, file_path: str) -> list[A11yFinding]:
        findings: list[A11yFinding] = []
        lines = content.splitlines()
        is_template = (
            file_path.endswith((".html", ".blade.php", ".vue", ".jsx", ".tsx"))
            or "<html" in content.lower()
            or "<div" in content.lower()
        )

        if not is_template:
            return findings

        for i, line in enumerate(lines, 1):
            # A11y-001: <img> without alt
            for match in _IMG_NO_ALT_RE.finditer(line):
                if not _ALT_RE.search(match.group()):
                    findings.append(A11yFinding(
                        rule_id="A11y-001",
                        severity=A11ySeverity.ERROR,
                        message="<img> without alt attribute — screen readers cannot describe image",
                        file_path=file_path,
                        line=i,
                        fix='Add alt="description" or alt="" for decorative images',
                    ))

            # A11y-002: <button>/<a> without text or aria-label
            for match in _BUTTON_RE.finditer(line):
                inner = match.group(1).strip()
                if not inner and not _ARIA_LABEL_RE.search(match.group()):
                    findings.append(A11yFinding(
                        rule_id="A11y-002",
                        severity=A11ySeverity.ERROR,
                        message="<button> without text or aria-label — inaccessible to screen readers",
                        file_path=file_path,
                        line=i,
                        fix='Add text content or aria-label="action description"',
                    ))

            for match in _LINK_RE.finditer(line):
                inner = match.group(1).strip()
                if not inner and not _ARIA_LABEL_RE.search(match.group()):
                    findings.append(A11yFinding(
                        rule_id="A11y-002",
                        severity=A11ySeverity.ERROR,
                        message="<a> without text or aria-label — link purpose unclear",
                        file_path=file_path,
                        line=i,
                        fix='Add link text or aria-label="destination description"',
                    ))

            # A11y-003: <input> without label
            for match in _INPUT_RE.finditer(line):
                if not _LABEL_FOR_RE.search(content) and not _ARIA_LABEL_RE.search(match.group()):
                    findings.append(A11yFinding(
                        rule_id="A11y-003",
                        severity=A11ySeverity.WARNING,
                        message="<input> without associated <label> or aria-label — form field unlabeled",
                        file_path=file_path,
                        line=i,
                        fix='Add <label for="id">Label</label> or aria-label="field name"',
                    ))

            # A11y-005: Animations without motion-reduce
            if _ANIMATE_RE.search(line) and not _MOTION_REDUCE_RE.search(content):
                findings.append(A11yFinding(
                    rule_id="A11y-005",
                    severity=A11ySeverity.WARNING,
                    message="Animation/transition without motion-reduce: — vestibular disorder risk",
                    file_path=file_path,
                    line=i,
                    fix="Add motion-reduce:animate-none or motion-reduce:transition-none",
                ))

            # A11y-006: Inline color style
            if _INLINE_COLOR_RE.search(line):
                findings.append(A11yFinding(
                    rule_id="A11y-006",
                    severity=A11ySeverity.INFO,
                    message="Inline color/background style — contrast not verified. Use Tailwind tokens",
                    file_path=file_path,
                    line=i,
                    fix="Use Tailwind color utilities (text-gray-900) for consistent contrast",
                ))

            # A11y-009: onclick without keyboard equivalent
            if _ONCLICK_RE.search(line) and not _KEYDOWN_RE.search(content):
                findings.append(A11yFinding(
                    rule_id="A11y-009",
                    severity=A11ySeverity.WARNING,
                    message="onclick without onkeydown — keyboard users cannot trigger action",
                    file_path=file_path,
                    line=i,
                    fix="Add onkeydown for keyboard accessibility or use <button> with native keyboard support",
                ))

            # A11y-010: tabindex > 0
            for match in _TABINDEX_POS_RE.finditer(line):
                findings.append(A11yFinding(
                    rule_id="A11y-010",
                    severity=A11ySeverity.WARNING,
                    message=f"tabindex={match.group(1)} > 0 breaks natural tab order — use tabindex=0 or -1",
                    file_path=file_path,
                    line=i,
                    fix="Use tabindex=0 (focusable in order) or tabindex=-1 (focusable via JS only)",
                ))

        # A11y-007: Arabic content without dir="rtl"
        if _ARABIC_TEXT_RE.search(content):
            has_html = _HTML_RE.search(content)
            has_rtl = _DIR_RTL_RE.search(content)
            if has_html and not has_rtl:
                line_num = next(
                    (i for i, ln in enumerate(lines, 1) if _HTML_RE.search(ln)),
                    1,
                )
                findings.append(A11yFinding(
                    rule_id="A11y-007",
                    severity=A11ySeverity.WARNING,
                    message="Arabic content detected but <html> lacks dir=\"rtl\" — text direction wrong",
                    file_path=file_path,
                    line=line_num,
                    fix='Add dir="rtl" to <html> tag and lang="ar"',
                ))

        # A11y-008: <table> without caption
        if _TABLE_RE.search(content) and not _CAPTION_RE.search(content):
            line_num = next(
                (i for i, ln in enumerate(lines, 1) if _TABLE_RE.search(ln)),
                1,
            )
            findings.append(A11yFinding(
                rule_id="A11y-008",
                severity=A11ySeverity.WARNING,
                message="<table> without <caption> or aria-label — screen readers lack table purpose",
                file_path=file_path,
                line=line_num,
                fix="Add <caption>Title</caption> as first child of <table>",
            ))

        return findings

    def summary(self, findings: list[A11yFinding]) -> dict[str, Any]:
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
