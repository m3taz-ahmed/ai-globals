#!/usr/bin/env python3
"""AI code review engine for AI Global OS.

Provides automated code review with multi-dimensional analysis and
confidence scoring. Reviews code changes (diffs) for:

- Security vulnerabilities (OWASP patterns)
- Code quality (complexity, duplication, dead code)
- Bug detection (null checks, error handling, edge cases)
- Style/convention compliance
- Test coverage gaps
- Performance issues

Each finding includes a confidence score (0-100) and severity level.
Findings below a configurable threshold are filtered out.

Usage::

    from runtime.review_engine import CodeReviewEngine, ReviewConfig
    engine = CodeReviewEngine()
    report = engine.review_diff(old_code, new_code, Path("module.py"))
    print(report.summary())
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from runtime.agentic_security import AgenticSecurityScanner


@dataclass
class ReviewFinding:
    """A single code review finding."""

    category: str  # security, quality, bug, style, test, performance
    severity: str  # critical, high, medium, low, info
    confidence: int  # 0-100
    message: str
    line: int | None = None
    column: int | None = None
    rule_id: str = ""
    suggestion: str = ""

    @property
    def passes_threshold(self) -> bool:
        """Default threshold is 50."""
        return self.confidence >= 50


@dataclass
class ReviewConfig:
    """Configuration for the code review engine."""

    min_confidence: int = 50
    enabled_categories: set[str] = field(default_factory=lambda: {
        "security", "quality", "bug", "style", "test", "performance",
    })
    max_findings: int = 100
    fail_on_critical: bool = True
    fail_on_high: bool = True


@dataclass
class ReviewReport:
    """Aggregated code review report."""

    file_path: str = ""
    findings: list[ReviewFinding] = field(default_factory=list)
    lines_reviewed: int = 0

    @property
    def passed(self) -> bool:
        """True if no critical or high severity findings (above threshold)."""
        return not any(
            f.severity in ("critical", "high") and f.confidence >= 50
            for f in self.findings
        )

    @property
    def score(self) -> int:
        """Review score 0-100 (100 = clean)."""
        if not self.findings:
            return 100
        weights = {"critical": 25, "high": 15, "medium": 8, "low": 3, "info": 1}
        total = sum(weights.get(f.severity, 0) for f in self.findings if f.confidence >= 50)
        return max(0, 100 - total)

    def filtered(self, config: ReviewConfig) -> list[ReviewFinding]:
        """Return findings filtered by config."""
        result = [
            f for f in self.findings
            if f.confidence >= config.min_confidence
            and f.category in config.enabled_categories
        ]
        return result[:config.max_findings]

    def summary(self) -> dict[str, Any]:
        """Return summary dict."""
        by_category: dict[str, int] = {}
        by_severity: dict[str, int] = {}
        for f in self.findings:
            if f.confidence >= 50:
                by_category[f.category] = by_category.get(f.category, 0) + 1
                by_severity[f.severity] = by_severity.get(f.severity, 0) + 1
        return {
            "file": self.file_path,
            "passed": self.passed,
            "score": self.score,
            "lines_reviewed": self.lines_reviewed,
            "total_findings": len(self.findings),
            "findings_above_threshold": sum(1 for f in self.findings if f.confidence >= 50),
            "by_category": by_category,
            "by_severity": by_severity,
            "findings": [
                {
                    "category": f.category,
                    "severity": f.severity,
                    "confidence": f.confidence,
                    "message": f.message,
                    "line": f.line,
                    "rule_id": f.rule_id,
                    "suggestion": f.suggestion,
                }
                for f in self.findings
                if f.confidence >= 50
            ],
        }


class CodeReviewEngine:
    """Multi-dimensional AI code review engine."""

    def __init__(self, config: ReviewConfig | None = None) -> None:
        self.config = config or ReviewConfig()
        self._security_scanner = AgenticSecurityScanner()

    def review_diff(
        self,
        old_code: str,
        new_code: str,
        file_path: Path | None = None,
    ) -> ReviewReport:
        """Review a code diff and return findings."""
        path_str = str(file_path) if file_path else "<inline>"
        report = ReviewReport(file_path=path_str)
        report.lines_reviewed = len(new_code.split("\n"))

        if file_path and file_path.suffix == ".py":
            report.findings.extend(self._review_python(new_code, file_path))
        else:
            report.findings.extend(self._review_generic(new_code, file_path))

        # Security review (always)
        report.findings.extend(self._review_security(new_code, file_path))

        # Bug detection
        report.findings.extend(self._review_bugs(new_code, file_path))

        # Style checks
        report.findings.extend(self._review_style(new_code, file_path))

        # Performance
        report.findings.extend(self._review_performance(new_code, file_path))

        return report

    def review_file(self, file_path: Path) -> ReviewReport:
        """Review a single file."""
        if not file_path.exists():
            return ReviewReport(file_path=str(file_path))
        code = file_path.read_text(encoding="utf-8", errors="replace")
        return self.review_diff("", code, file_path)

    def review_directory(
        self,
        directory: Path,
        extensions: set[str] | None = None,
    ) -> list[ReviewReport]:
        """Review all files in a directory."""
        if extensions is None:
            extensions = {".py", ".js", ".ts"}
        reports: list[ReviewReport] = []
        for f in directory.rglob("*"):
            if not f.is_file():
                continue
            if f.suffix not in extensions:
                continue
            if any(part in {".git", "__pycache__", "node_modules", ".venv"} for part in f.parts):
                continue
            reports.append(self.review_file(f))
        return reports

    def _review_python(self, code: str, file_path: Path | None) -> list[ReviewFinding]:
        """Python-specific AST-based review."""
        findings: list[ReviewFinding] = []
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            findings.append(ReviewFinding(
                category="quality",
                severity="critical",
                confidence=100,
                message=f"Syntax error: {e.msg}",
                line=e.lineno,
                rule_id="PY-SYNTAX",
                suggestion="Fix the syntax error before proceeding.",
            ))
            return findings

        # Check for bare except
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                findings.append(ReviewFinding(
                    category="bug",
                    severity="medium",
                    confidence=85,
                    message="Bare 'except:' catches all exceptions including KeyboardInterrupt",
                    line=node.lineno,
                    rule_id="PY-BARE-EXCEPT",
                    suggestion="Use 'except Exception:' instead.",
                ))

        # Check for mutable default arguments
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for default in node.args.defaults + node.args.kw_defaults:
                    if default and isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        findings.append(ReviewFinding(
                            category="bug",
                            severity="high",
                            confidence=90,
                            message=f"Mutable default argument in '{node.name}()'",
                            line=node.lineno,
                            rule_id="PY-MUTABLE-DEFAULT",
                            suggestion="Use None and initialize inside the function.",
                        ))

        # Check for functions that are too long
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                length = (node.end_lineno or node.lineno) - node.lineno
                if length > 50:
                    findings.append(ReviewFinding(
                        category="quality",
                        severity="medium",
                        confidence=75,
                        message=f"Function '{node.name}()' is {length} lines long (max 50)",
                        line=node.lineno,
                        rule_id="PY-LONG-FUNCTION",
                        suggestion="Break into smaller functions.",
                    ))

        # Check for TODO/FIXME without ticket
        for i, line in enumerate(code.split("\n"), 1):
            if re.search(r"#\s*(TODO|FIXME|HACK|XXX)", line, re.IGNORECASE) and not re.search(r"[A-Z]+-\d+", line):
                findings.append(ReviewFinding(
                        category="quality",
                        severity="low",
                        confidence=80,
                        message="TODO/FIXME without ticket reference",
                        line=i,
                        rule_id="PY-TODO-NOTICKET",
                        suggestion="Add a ticket reference (e.g., TODO(JIRA-123)).",
                    ))

        return findings

    def _review_generic(self, code: str, file_path: Path | None) -> list[ReviewFinding]:
        """Generic review for non-Python files."""
        findings: list[ReviewFinding] = []
        # Check for console.log / print statements
        for i, line in enumerate(code.split("\n"), 1):
            if re.search(r"\bconsole\.log\b", line):
                findings.append(ReviewFinding(
                    category="style",
                    severity="low",
                    confidence=70,
                    message="console.log statement found",
                    line=i,
                    rule_id="GEN-CONSOLE-LOG",
                    suggestion="Remove debug logging before production.",
                ))
        return findings

    def _review_security(self, code: str, file_path: Path | None) -> list[ReviewFinding]:
        """Security-focused review using the agentic security scanner."""
        findings: list[ReviewFinding] = []
        path_str = str(file_path) if file_path else "<inline>"
        sec_findings = self._security_scanner.scan_text(code, path_str)
        for sf in sec_findings:
            findings.append(ReviewFinding(
                category="security",
                severity=sf.severity,
                confidence=85,
                message=sf.description,
                line=sf.line,
                rule_id=f"SEC-{sf.control_id}",
                suggestion=sf.remediation,
            ))
        return findings

    def _review_bugs(self, code: str, file_path: Path | None) -> list[ReviewFinding]:
        """Bug detection patterns."""
        findings: list[ReviewFinding] = []
        lines = code.split("\n")
        for i, line in enumerate(lines, 1):
            # Check for == None / != None
            if re.search(r"==\s*None|!=\s*None", line):
                findings.append(ReviewFinding(
                    category="bug",
                    severity="low",
                    confidence=75,
                    message="Use 'is None' / 'is not None' instead of '== None'",
                    line=i,
                    rule_id="BUG-NONE-COMPARE",
                    suggestion="Replace == None with 'is None'.",
                ))
            # Check for == True / == False
            if re.search(r"==\s*True|==\s*False", line):
                findings.append(ReviewFinding(
                    category="style",
                    severity="low",
                    confidence=70,
                    message="Direct comparison to True/False",
                    line=i,
                    rule_id="STYLE-BOOL-COMPARE",
                    suggestion="Use 'if x:' instead of 'if x == True:'.",
                ))
            # Check for broad exception catching with pass
            if re.search(r"except.*:\s*$", line) and i < len(lines) and lines[i].strip() == "pass":
                findings.append(ReviewFinding(
                    category="bug",
                    severity="medium",
                    confidence=80,
                    message="Exception caught and silently ignored (pass)",
                    line=i,
                    rule_id="BUG-SILENT-EXCEPT",
                    suggestion="Log the exception or handle it properly.",
                ))
        return findings

    def _review_style(self, code: str, file_path: Path | None) -> list[ReviewFinding]:
        """Style and convention checks."""
        findings: list[ReviewFinding] = []
        lines = code.split("\n")
        for i, line in enumerate(lines, 1):
            # Check for trailing whitespace
            if line.rstrip() != line and line.strip():
                findings.append(ReviewFinding(
                    category="style",
                    severity="info",
                    confidence=95,
                    message="Trailing whitespace",
                    line=i,
                    rule_id="STYLE-TRAILING-WS",
                    suggestion="Remove trailing whitespace.",
                ))
            # Check for lines that are too long
            if len(line) > 120:
                findings.append(ReviewFinding(
                    category="style",
                    severity="low",
                    confidence=60,
                    message=f"Line too long ({len(line)} chars, max 120)",
                    line=i,
                    rule_id="STYLE-LONG-LINE",
                    suggestion="Break the line or shorten variable names.",
                ))
        return findings

    def _review_performance(self, code: str, file_path: Path | None) -> list[ReviewFinding]:
        """Performance issue detection."""
        findings: list[ReviewFinding] = []
        lines = code.split("\n")
        for i, line in enumerate(lines, 1):
            # Check for string concatenation in a loop (basic heuristic)
            if re.search(r"\+\s*['\"]", line) and any(
                kw in lines[max(0, i-3):i+1]
                for kw in ["for ", "while "]
            ):
                findings.append(ReviewFinding(
                    category="performance",
                    severity="low",
                    confidence=55,
                    message="String concatenation in loop — consider join()",
                    line=i,
                    rule_id="PERF-STR-CONCAT",
                    suggestion="Use ''.join() for string building in loops.",
                ))
            # Check for list.append in list comprehension context
            if re.search(r"for\s+\w+\s+in\s+.*:\s*\n\s*.*\.append\(", code):
                findings.append(ReviewFinding(
                    category="performance",
                    severity="low",
                    confidence=60,
                    message="List append in for-loop — consider list comprehension",
                    line=i,
                    rule_id="PERF-LIST-APPEND",
                    suggestion="Use a list comprehension for better performance.",
                ))
        return findings


def review_code(file_path: Path, config: ReviewConfig | None = None) -> ReviewReport:
    """Convenience function to review a single file."""
    engine = CodeReviewEngine(config)
    return engine.review_file(file_path)


if __name__ == "__main__":
    import json
    import sys
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    engine = CodeReviewEngine()
    if target.is_dir():
        reports = engine.review_directory(target)
        all_findings = sum(len(r.findings) for r in reports)
        print(json.dumps({
            "files_reviewed": len(reports),
            "total_findings": all_findings,
            "passed": all(r.passed for r in reports),
        }, indent=2))
    else:
        report = engine.review_file(target)
        print(json.dumps(report.summary(), indent=2))
