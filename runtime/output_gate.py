"""Pre-send output gate with portability test.

Combines patterns from i-have-adhd (ayghri/i-have-adhd) pre-send
check and no-ai-slop (petergyang/no-ai-slop) portability test.
Runs a final quality check on aiZee's output before it reaches the
user: removes preamble/recap/closers, flags hedging adverbs, detects
generic (portable) sentences, and verifies the first/last line test.

Usage::

    from runtime.output_gate import check_output, OutputCheckResult
    result = check_output(my_response)
    if result.issues:
        # Fix and re-check before sending
        ...
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# Banned openers (i-have-adhd SKILL.md).
_BANNED_OPENERS: tuple[str, ...] = (
    "great question", "let me", "i'll", "sure!", "looking at your",
    "to answer your question", "here's the thing", "let me be clear",
    "i'll be honest", "the uncomfortable truth is",
)

# Banned closers.
_BANNED_CLOSERS: tuple[str, ...] = (
    "let me know if you need anything else",
    "hope this helps",
    "happy to clarify",
    "feel free to ask",
    "let me know if you want to dig deeper",
    "hope that helps",
)

# Banned recaps (start of line).
_BANNED_RECAP_PATTERNS: tuple[str, ...] = (
    r"^i've now done .*, which means",
    r"^i've made some changes.*among other things",
    r"^so to summarize",
    r"^in summary,",
)

# Hedging adverbs that add no information.
_HEDGING_ADVERBS: tuple[str, ...] = (
    "perhaps", "might possibly", "could possibly", "potentially",
    "arguably", "supposedly", "presumably",
)

# Idioms to replace with literal actions.
_IDIOMS: tuple[str, ...] = (
    "circle back", "get the ball rolling", "on the same page",
    "touch base", "low-hanging fruit", "move the needle",
    "boil the ocean", "herding cats",
)

# Generic phrases that fail the portability test (could apply to anything).
_GENERIC_PHRASES: tuple[str, ...] = (
    "significantly improves",
    "enhances productivity",
    "streamlines workflows",
    "leverages cutting-edge",
    "robust solution",
    "comprehensive approach",
    "seamless integration",
    "transformative impact",
)


@dataclass
class OutputIssue:
    """One issue found by the output gate."""

    category: str
    severity: str  # "error", "warning", "info"
    line: int
    text: str
    suggestion: str = ""


@dataclass
class OutputCheckResult:
    """Result of checking output through the gate."""

    issues: list[OutputIssue] = field(default_factory=list)
    original_text: str = ""
    first_line: str = ""
    last_line: str = ""

    @property
    def passed(self) -> bool:
        """True if no error-severity issues."""
        return not any(i.severity == "error" for i in self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "issues": [
                {
                    "category": i.category,
                    "severity": i.severity,
                    "line": i.line,
                    "text": i.text,
                    "suggestion": i.suggestion,
                }
                for i in self.issues
            ],
        }


def _get_lines(text: str) -> list[str]:
    """Split text into non-empty lines."""
    return [line for line in text.splitlines() if line.strip()]


def _check_openers(lines: list[str]) -> list[OutputIssue]:
    """Check for banned preamble openers."""
    issues: list[OutputIssue] = []
    if not lines:
        return issues
    first = lines[0].strip().lower()
    for opener in _BANNED_OPENERS:
        if first.startswith(opener):
            issues.append(OutputIssue(
                category="preamble",
                severity="error",
                line=1,
                text=lines[0].strip(),
                suggestion=f'Delete the opener "{opener}" and start with the answer.',
            ))
            break
    return issues


def _check_closers(lines: list[str]) -> list[OutputIssue]:
    """Check for banned closing pleasantries."""
    issues: list[OutputIssue] = []
    if not lines:
        return issues
    last = lines[-1].strip().lower()
    for closer in _BANNED_CLOSERS:
        if closer in last:
            issues.append(OutputIssue(
                category="closer",
                severity="error",
                line=len(lines),
                text=lines[-1].strip(),
                suggestion='Delete the closer and end on the last concrete point.',
            ))
            break
    return issues


def _check_recaps(text: str) -> list[OutputIssue]:
    """Check for banned recap patterns."""
    issues: list[OutputIssue] = []
    for i, line in enumerate(text.splitlines(), 1):
        stripped = line.strip().lower()
        for pattern in _BANNED_RECAP_PATTERNS:
            if re.match(pattern, stripped):
                issues.append(OutputIssue(
                    category="recap",
                    severity="warning",
                    line=i,
                    text=line.strip(),
                    suggestion="Delete the recap — the reader was just there.",
                ))
                break
    return issues


def _check_hedging(text: str) -> list[OutputIssue]:
    """Check for hedging adverbs that add no information."""
    issues: list[OutputIssue] = []
    text.lower()
    for i, line in enumerate(text.splitlines(), 1):
        line_lower = line.lower()
        for adverb in _HEDGING_ADVERBS:
            if adverb in line_lower:
                issues.append(OutputIssue(
                    category="hedging",
                    severity="warning",
                    line=i,
                    text=line.strip(),
                    suggestion=f'Remove "{adverb}" unless it carries real uncertainty.',
                ))
                break
    return issues


def _check_idioms(text: str) -> list[OutputIssue]:
    """Check for idioms that should be replaced with literal actions."""
    issues: list[OutputIssue] = []
    for i, line in enumerate(text.splitlines(), 1):
        line_lower = line.lower()
        for idiom in _IDIOMS:
            if idiom in line_lower:
                issues.append(OutputIssue(
                    category="idiom",
                    severity="warning",
                    line=i,
                    text=line.strip(),
                    suggestion=f'Replace "{idiom}" with the literal action.',
                ))
                break
    return issues


def _check_portability(text: str) -> list[OutputIssue]:
    """Check for generic phrases that fail the portability test."""
    issues: list[OutputIssue] = []
    for i, line in enumerate(text.splitlines(), 1):
        line_lower = line.lower()
        for phrase in _GENERIC_PHRASES:
            if phrase in line_lower:
                issues.append(OutputIssue(
                    category="portability",
                    severity="warning",
                    line=i,
                    text=line.strip(),
                    suggestion=(
                        f'"{phrase}" could apply to any project. '
                        "Replace with a fact, example, or mechanism specific to this subject."
                    ),
                ))
                break
    return issues


def _check_first_last_line_test(lines: list[str]) -> list[OutputIssue]:
    """Verify: if the reader reads only first + last line, do they know
    (a) what to do next and (b) what just happened?"""
    issues: list[OutputIssue] = []
    if len(lines) < 2:
        return issues
    first = lines[0].strip()
    lines[-1].strip()
    # Heuristic: first line should contain an action verb or command
    action_indicators = ("run ", "edit ", "open ", "check ", "create ", "delete ",
                         "update ", "add ", "fix ", "install ", "test ", "use ",
                         "next:", "step", "1.", "2.")
    first_lower = first.lower()
    has_action = any(first_lower.startswith(ind) or f" {ind}" in first_lower for ind in action_indicators)
    is_direct_answer = first.endswith("?") or first.endswith(":")
    if not has_action and not is_direct_answer:
        issues.append(OutputIssue(
            category="first-line",
            severity="info",
            line=1,
            text=first,
            suggestion="First line should be an action the reader can do, or a direct answer.",
        ))
    return issues


def check_output(text: str) -> OutputCheckResult:
    """Run all output gate checks on *text*.

    Returns an :class:`OutputCheckResult` with all issues found.
    The ``passed`` property is True if no error-severity issues exist.
    """
    if not text or not text.strip():
        return OutputCheckResult(original_text=text)

    lines = _get_lines(text)
    result = OutputCheckResult(
        original_text=text,
        first_line=lines[0].strip() if lines else "",
        last_line=lines[-1].strip() if lines else "",
    )

    result.issues.extend(_check_openers(lines))
    result.issues.extend(_check_closers(lines))
    result.issues.extend(_check_recaps(text))
    result.issues.extend(_check_hedging(text))
    result.issues.extend(_check_idioms(text))
    result.issues.extend(_check_portability(text))
    result.issues.extend(_check_first_last_line_test(lines))

    return result


def auto_fix(text: str) -> tuple[str, list[OutputIssue]]:
    """Attempt automatic fixes for the most common issues.

    Returns (fixed_text, remaining_issues). Only fixes that are safe
    to apply automatically (deleting preamble/closers) are performed;
    warnings (hedging, idioms, portability) are left for manual review.
    """
    if not text or not text.strip():
        return text, []

    lines = text.splitlines()
    # Find and strip banned opener prefix from the first non-empty line.
    # Only removes the opener phrase, not the entire line — the rest of
    # the line may contain the actual answer. Strips chained openers
    # (e.g. "Great question! Let me think..." → "think...").
    fixed_lines: list[str] = []
    skipped_opener = False
    for i, line in enumerate(lines):
        if not line.strip():
            fixed_lines.append(line)
            continue
        if not skipped_opener and i == 0:
            stripped = line.lstrip()
            # Repeatedly strip openers until none remain
            changed = True
            while changed:
                changed = False
                lower = stripped.lower()
                for opener in _BANNED_OPENERS:
                    if lower.startswith(opener):
                        stripped = stripped[len(opener):].lstrip()
                        stripped = stripped.lstrip("!.,:;")
                        stripped = stripped.lstrip()
                        changed = True
                        break
            skipped_opener = True
            if stripped:
                fixed_lines.append(stripped)
            continue
        fixed_lines.append(line)

    # Find and remove banned closers (last non-empty line).
    # If the closer is a sentence within a longer line, strip only
    # the closer sentence, not the entire line. Repeatedly strip
    # chained closers (e.g. "Hope this helps! Let me know...").
    final_lines: list[str] = []
    skipped_closer = False
    for line in reversed(fixed_lines):
        if not line.strip():
            final_lines.insert(0, line)
            continue
        if not skipped_closer:
            stripped_line = line.rstrip()
            # Repeatedly strip closers from the end until none remain
            changed = True
            while changed:
                changed = False
                lower = stripped_line.lower()
                for closer in _BANNED_CLOSERS:
                    if closer in lower:
                        idx = lower.rfind(closer)
                        before = stripped_line[:idx].rstrip()
                        before = before.rstrip(".!?,;: ")
                        stripped_line = before
                        changed = True
                        skipped_closer = True
                        break
            if stripped_line:
                final_lines.insert(0, stripped_line)
            continue
        final_lines.insert(0, line)

    fixed_text = "\n".join(final_lines).rstrip()
    # Re-check remaining issues
    remaining = check_output(fixed_text)
    # Only return non-auto-fixable issues
    auto_fixed: list[OutputIssue] = []
    if skipped_opener:
        auto_fixed.append(OutputIssue("preamble", "error", 1, "(removed)"))
    if skipped_closer:
        auto_fixed.append(OutputIssue("closer", "error", -1, "(removed)"))

    return fixed_text, remaining.issues
