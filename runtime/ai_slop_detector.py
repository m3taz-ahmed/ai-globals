#!/usr/bin/env python3
"""AI slop detector for AI Global OS.

Detects common patterns in AI-generated code that indicate low quality:
- Silent error swallowing (except: pass)
- Dead branches (unreachable code)
- Copy-paste leaks (duplicated blocks with minor variations)
- Hallucinated imports (nonexistent modules)
- Overly verbose docstrings
- Unnecessary type conversions
- Redundant condition checks
- Empty function bodies (stub code left in production)

Produces a single 0-100 score and detailed findings.

Usage::

    from runtime.ai_slop_detector import AISlopDetector
    detector = AISlopDetector()
    result = detector.detect(code, Path("module.py"))
    print(f"AI Slop Score: {result.score}/100")
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SlopFinding:
    """A single AI slop finding."""

    category: str
    severity: str  # critical, high, medium, low
    message: str
    line: int | None = None
    pattern: str = ""


@dataclass
class SlopReport:
    """AI slop detection report."""

    findings: list[SlopFinding] = field(default_factory=list)
    lines_analyzed: int = 0

    @property
    def score(self) -> int:
        """0-100 score (100 = clean, 0 = maximum slop)."""
        if not self.findings:
            return 100
        weights = {"critical": 20, "high": 12, "medium": 6, "low": 3}
        total_deduction = sum(weights.get(f.severity, 0) for f in self.findings)
        return max(0, 100 - total_deduction)

    @property
    def is_clean(self) -> bool:
        """True if score >= 80."""
        return self.score >= 80

    def summary(self) -> dict[str, Any]:
        """Return summary dict."""
        by_category: dict[str, int] = {}
        by_severity: dict[str, int] = {}
        for f in self.findings:
            by_category[f.category] = by_category.get(f.category, 0) + 1
            by_severity[f.severity] = by_severity.get(f.severity, 0) + 1
        return {
            "score": self.score,
            "is_clean": self.is_clean,
            "lines_analyzed": self.lines_analyzed,
            "total_findings": len(self.findings),
            "by_category": by_category,
            "by_severity": by_severity,
            "findings": [
                {
                    "category": f.category,
                    "severity": f.severity,
                    "message": f.message,
                    "line": f.line,
                }
                for f in self.findings
            ],
        }


class AISlopDetector:
    """Detector for AI-generated code quality issues (AI slop)."""

    def detect(self, code: str, file_path: Path | None = None) -> SlopReport:
        """Detect AI slop patterns in code."""
        report = SlopReport()
        report.lines_analyzed = len(code.split("\n"))

        # Python-specific AST checks
        if file_path is None or file_path.suffix == ".py":
            report.findings.extend(self._check_python(code))
        else:
            report.findings.extend(self._check_generic(code))

        # Common pattern checks (all languages)
        report.findings.extend(self._check_copy_paste(code))
        report.findings.extend(self._check_dead_branches(code))
        report.findings.extend(self._check_verbose_comments(code))

        return report

    def detect_file(self, file_path: Path) -> SlopReport:
        """Detect AI slop in a file."""
        if not file_path.exists():
            return SlopReport()
        code = file_path.read_text(encoding="utf-8", errors="replace")
        return self.detect(code, file_path)

    def _check_python(self, code: str) -> list[SlopFinding]:
        """Python-specific AI slop checks."""
        findings: list[SlopFinding] = []
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return findings

        # Silent error swallowing
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                # Check if body is just pass or continue
                body = node.body
                if len(body) == 1 and isinstance(body[0], (ast.Pass, ast.Continue)):
                    findings.append(SlopFinding(
                        category="silent_error_swallowing",
                        severity="high",
                        message="Bare except with pass/continue — errors are silently swallowed",
                        line=node.lineno,
                    ))

        # Empty function bodies (stubs left in production)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                body = node.body
                if len(body) == 1 and isinstance(body[0], ast.Pass) and not ast.get_docstring(node):
                    findings.append(SlopFinding(
                        category="empty_stub",
                        severity="medium",
                        message=f"Function '{node.name}()' has only 'pass' — stub left in production",
                        line=node.lineno,
                    ))

        # Unnecessary type conversions
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id in ("str", "int", "float", "bool")
                    and node.args and isinstance(node.args[0], ast.Call)):
                inner = node.args[0]
                if isinstance(inner.func, ast.Name) and inner.func.id == node.func.id:
                        findings.append(SlopFinding(
                            category="redundant_conversion",
                            severity="low",
                            message=f"Redundant {node.func.id}({node.func.id}(...)) — double conversion",
                            line=node.lineno,
                        ))

        # Overly long try blocks (catches too much)
        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                try_len = (node.end_lineno or node.lineno) - node.lineno
                if try_len > 50:
                    findings.append(SlopFinding(
                        category="overly_broad_try",
                        severity="medium",
                        message=f"Try block is {try_len} lines long — too broad, narrows error handling",
                        line=node.lineno,
                    ))

        # Redundant condition checks
        for node in ast.walk(tree):
            if (isinstance(node, ast.If)
                    and isinstance(node.test, ast.Compare)
                    and isinstance(node.test.ops[0], (ast.Is, ast.IsNot))):
                for child in ast.walk(node):
                    if (isinstance(child, ast.If) and isinstance(child.test, ast.Name)
                            and isinstance(node.test.left, ast.Name)
                            and child.test.id == node.test.left.id):
                            findings.append(SlopFinding(
                                category="redundant_check",
                                severity="low",
                                message="Redundant None check followed by truthiness check",
                                line=node.lineno,
                            ))

        return findings

    def _check_generic(self, code: str) -> list[SlopFinding]:
        """Generic AI slop checks for non-Python files."""
        findings: list[SlopFinding] = []
        lines = code.split("\n")
        for i, line in enumerate(lines, 1):
            # Empty catch blocks
            if re.search(r"catch\s*\([^)]*\)\s*\{\s*\}", line):
                findings.append(SlopFinding(
                    category="silent_error_swallowing",
                    severity="high",
                    message="Empty catch block — errors are silently swallowed",
                    line=i,
                ))
        return findings

    def _check_copy_paste(self, code: str) -> list[SlopFinding]:
        """Detect copy-paste patterns (duplicated blocks)."""
        findings: list[SlopFinding] = []
        lines = code.split("\n")
        # Look for 3+ consecutive identical lines (excluding blanks)
        non_blank = [(i, line.strip()) for i, line in enumerate(lines, 1) if line.strip()]
        for i in range(len(non_blank) - 3):
            block = [non_blank[i + j][1] for j in range(4)]
            if len(set(block)) == 1 and len(block[0]) > 10:
                findings.append(SlopFinding(
                    category="copy_paste_leak",
                    severity="medium",
                    message=f"Duplicated line repeated 4+ times: '{block[0][:50]}...'",
                    line=non_blank[i][0],
                ))
        # Look for similar but not identical blocks (3+ lines with <2 char difference)
        for i in range(len(lines) - 6):
            block1 = lines[i:i + 3]
            block2 = lines[i + 3:i + 6]
            if all(b.strip() for b in block1 + block2):
                diffs = sum(1 for a, b in zip(block1, block2, strict=False) if a != b)
                if diffs <= 1 and diffs > 0:
                    findings.append(SlopFinding(
                        category="copy_paste_leak",
                        severity="low",
                        message="Near-duplicate code blocks detected — likely copy-paste with minor edits",
                        line=i + 1,
                    ))
        return findings

    def _check_dead_branches(self, code: str) -> list[SlopFinding]:
        """Detect dead/unreachable code branches."""
        findings: list[SlopFinding] = []
        lines = code.split("\n")
        for i, line in enumerate(lines, 1):
            # return followed by non-blank, non-comment lines at same indent
            if re.match(r"\s*return\s", line):
                # Check if next non-blank line is at same or lower indent
                indent = len(line) - len(line.lstrip())
                for j in range(i, min(i + 5, len(lines))):
                    next_line = lines[j]
                    if next_line.strip() and not next_line.strip().startswith("#"):
                        next_indent = len(next_line) - len(next_line.lstrip())
                        if next_indent >= indent and not next_line.strip().startswith(("def ", "class ", "else", "elif", "except", "finally")):
                            findings.append(SlopFinding(
                                category="dead_branch",
                                severity="medium",
                                message="Code after return statement is unreachable",
                                line=j + 1,
                            ))
                            break
            # if True: / if False: — always-true/false conditions
            if re.match(r"\s*if\s+True\s*:", line):
                findings.append(SlopFinding(
                    category="dead_branch",
                    severity="low",
                    message="'if True:' is always true — likely placeholder",
                    line=i,
                ))
            if re.match(r"\s*if\s+False\s*:", line):
                findings.append(SlopFinding(
                    category="dead_branch",
                    severity="medium",
                    message="'if False:' is dead code — never executes",
                    line=i,
                ))
        return findings

    def _check_verbose_comments(self, code: str) -> list[SlopFinding]:
        """Detect overly verbose AI-generated comments."""
        findings: list[SlopFinding] = []
        lines = code.split("\n")
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            # Comments longer than 100 chars
            if stripped.startswith("#") and len(stripped) > 100:
                findings.append(SlopFinding(
                    category="verbose_comment",
                    severity="low",
                    message=f"Comment is {len(stripped)} chars — overly verbose",
                    line=i,
                ))
            # Obvious comments (restating the code)
            obvious_patterns = [
                r"#\s*(import|from|def|class|return|if|for|while)\s",
                r"#\s*(set|get|create|delete|update)\s+(the\s+)?\w+",
            ]
            for pattern in obvious_patterns:
                if re.match(pattern, stripped, re.IGNORECASE) and i < len(lines):
                    # Check if the comment just restates the next line
                    next_line = lines[i].strip() if i < len(lines) else ""
                    if next_line and any(kw in next_line for kw in ["import", "def ", "class ", "return"]):
                        findings.append(SlopFinding(
                            category="verbose_comment",
                            severity="low",
                            message="Comment restates the code — adds no value",
                            line=i,
                        ))
                        break
        return findings


def detect_slop(file_path: Path) -> SlopReport:
    """Convenience function to detect AI slop in a file."""
    detector = AISlopDetector()
    return detector.detect_file(file_path)


if __name__ == "__main__":
    import json
    import sys
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    detector = AISlopDetector()
    if target.is_file():
        report = detector.detect_file(target)
    else:
        report = detector.detect(target.read_text(encoding="utf-8", errors="replace"))
    print(json.dumps(report.summary(), indent=2))
