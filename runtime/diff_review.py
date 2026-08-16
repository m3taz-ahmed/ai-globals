#!/usr/bin/env python3
"""Diff-based code review (from open-code-review).

Reviews only changed lines (diff-based) instead of full file analysis.
Extracts hunks from unified diff format and reviews only those.

Usage::

    from runtime.diff_review import DiffReviewer

    reviewer = DiffReviewer()
    report = reviewer.review_diff(unified_diff_text)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from runtime.review_engine import CodeReviewEngine, ReviewReport


@dataclass
class DiffHunk:
    """A single hunk from a unified diff."""

    file_path: str
    old_start: int
    new_start: int
    added_lines: list[tuple[int, str]] = field(default_factory=list)
    removed_lines: list[tuple[int, str]] = field(default_factory=list)
    context_lines: list[tuple[int, str]] = field(default_factory=list)


@dataclass
class DiffParser:
    """Parse unified diff format into hunks."""

    @staticmethod
    def parse(diff_text: str) -> list[DiffHunk]:
        """Parse unified diff text into hunks."""
        hunks: list[DiffHunk] = []
        current_hunk: DiffHunk | None = None
        new_line_num = 0
        old_line_num = 0

        for line in diff_text.split("\n"):
            if line.startswith("+++ ") or line.startswith("--- "):
                continue
            if line.startswith("@@"):
                if current_hunk:
                    hunks.append(current_hunk)
                match = re.match(r"@@ -(\d+),?\d* \+(\d+),?\d* @@", line)
                if match:
                    old_start = int(match.group(1))
                    new_start = int(match.group(2))
                    # Extract file path from previous --- line
                    file_path = ""
                    current_hunk = DiffHunk(
                        file_path=file_path,
                        old_start=old_start,
                        new_start=new_start,
                    )
                    old_line_num = old_start
                    new_line_num = new_start
            elif current_hunk:
                if line.startswith("+"):
                    current_hunk.added_lines.append((new_line_num, line[1:]))
                    new_line_num += 1
                elif line.startswith("-"):
                    current_hunk.removed_lines.append((old_line_num, line[1:]))
                    old_line_num += 1
                elif line.startswith(" "):
                    current_hunk.context_lines.append((new_line_num, line[1:]))
                    old_line_num += 1
                    new_line_num += 1

        if current_hunk:
            hunks.append(current_hunk)
        return hunks

    @staticmethod
    def extract_file_paths(diff_text: str) -> list[str]:
        """Extract file paths from diff."""
        paths: list[str] = []
        for line in diff_text.split("\n"):
            if line.startswith("+++ b/"):
                paths.append(line[6:])
            elif line.startswith("+++ ") and not line.startswith("+++ /dev/null"):
                paths.append(line[4:])
        return paths


@dataclass
class DiffReviewer:
    """Review only changed lines in a diff (from open-code-review).

    More efficient than full-file review — only analyzes added/modified
    lines and their immediate context.
    """

    engine: CodeReviewEngine = field(default_factory=CodeReviewEngine)

    def review_diff(self, diff_text: str) -> list[ReviewReport]:
        """Review a unified diff and return reports per file."""
        hunks = DiffParser.parse(diff_text)
        reports: list[ReviewReport] = []
        for hunk in hunks:
            if not hunk.added_lines:
                continue
            # Build a pseudo-source from added lines + context
            lines = hunk.context_lines + hunk.added_lines
            source = "\n".join(line for _, line in lines)
            report = self.engine.review_diff("", source, Path(hunk.file_path))
            # Adjust line numbers to match the diff
            for finding in report.findings:
                if finding.line:
                    finding.line += hunk.new_start - 1
            reports.append(report)
        return reports

    def review_diff_summary(self, diff_text: str) -> dict[str, Any]:
        """Get a summary of diff review results."""
        reports = self.review_diff(diff_text)
        total_findings = sum(len(r.findings) for r in reports)
        return {
            "files_reviewed": len(reports),
            "total_findings": total_findings,
            "all_passed": all(r.passed for r in reports),
            "reports": [r.summary() for r in reports],
        }


if __name__ == "__main__":
    sample_diff = """--- a/test.py
+++ b/test.py
@@ -1,3 +1,4 @@
 def foo():
-    pass
+    x = None
+    if x == None:
+        return True
"""
    reviewer = DiffReviewer()
    summary = reviewer.review_diff_summary(sample_diff)
    print(f"Findings: {summary['total_findings']}")
