"""Self-checking skill evaluation engine.

Ported from no-ai-slop (petergyang/no-ai-slop) ``eval.md`` pattern.
Each aiZee skill can include an optional ``EVAL.md`` file alongside
its ``SKILL.md``. The eval file defines self-checks the skill runs
on its own output after execution. This module loads, parses, and
runs those checks.

EVAL.md format (Markdown with structured sections)::

    # Skill name eval

    Use this after the skill runs. Answer each check with pass or fail.

    ## Category 1

    1. Does the output ... ?
    2. Does the output ... ?

    ## Category 2

    1. Is ... ?

Each numbered item under a ``##`` heading is one check. The engine
extracts them and provides a :class:`SkillEvalResult` with per-check
pass/fail/skip status.

The checks are evaluated by an LLM (or a rule-based evaluator) — this
module provides the infrastructure (loading, parsing, result tracking),
not the LLM judgment itself. Callers supply an ``evaluator`` callable
that takes a check string + the skill output and returns
``"pass"``/``"fail"``/``"skip"``.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

_logger = logging.getLogger(__name__)


class CheckStatus(str, Enum):
    """Status of a single eval check."""

    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    ERROR = "error"


@dataclass
class EvalCheck:
    """One self-check extracted from an EVAL.md file."""

    category: str
    index: int  # 1-based index within the category
    text: str  # The check question/statement


@dataclass
class CheckResult:
    """Result of evaluating one check."""

    check: EvalCheck
    status: CheckStatus
    detail: str = ""


@dataclass
class SkillEvalResult:
    """Aggregate result of running all checks for a skill."""

    skill_name: str
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.checks)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.checks if r.status == CheckStatus.PASS)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.checks if r.status == CheckStatus.FAIL)

    @property
    def skipped(self) -> int:
        return sum(1 for r in self.checks if r.status == CheckStatus.SKIP)

    @property
    def errors(self) -> int:
        return sum(1 for r in self.checks if r.status == CheckStatus.ERROR)

    @property
    def all_passed(self) -> bool:
        """True if all checks passed (ignoring skips)."""
        return self.failed == 0 and self.errors == 0 and self.passed > 0

    @property
    def pass_rate(self) -> float:
        """Fraction of non-skipped checks that passed (0.0-1.0)."""
        evaluated = self.passed + self.failed
        if evaluated == 0:
            return 0.0
        return self.passed / evaluated

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_name": self.skill_name,
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "errors": self.errors,
            "all_passed": self.all_passed,
            "pass_rate": round(self.pass_rate, 4),
            "checks": [
                {
                    "category": r.check.category,
                    "index": r.check.index,
                    "text": r.check.text,
                    "status": r.status.value,
                    "detail": r.detail,
                }
                for r in self.checks
            ],
        }


# Type alias for the evaluator callable.
Evaluator = Callable[[str, str], str]


def parse_eval_md(content: str) -> list[EvalCheck]:
    """Parse an EVAL.md file content into a list of checks.

    Recognizes ``## Category`` headings and numbered items
    (``1. ...``, ``2. ...``) under each heading. Non-numbered lines
    and lines outside headings are ignored.
    """
    checks: list[EvalCheck] = []
    current_category = ""
    category_index = 0

    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        # Heading: ## Category Name
        heading_match = re.match(r"^#{1,6}\s+(.+)$", stripped)
        if heading_match:
            current_category = heading_match.group(1).strip()
            category_index = 0
            continue

        # Numbered item: 1. Check text
        item_match = re.match(r"^(\d+)\.\s+(.+)$", stripped)
        if item_match and current_category:
            category_index += 1
            checks.append(
                EvalCheck(
                    category=current_category,
                    index=category_index,
                    text=item_match.group(2).strip(),
                )
            )

    return checks


def load_eval_file(skill_dir: Path) -> list[EvalCheck] | None:
    """Load and parse ``EVAL.md`` from a skill directory.

    Returns ``None`` if no ``EVAL.md`` exists. Returns an empty list
    if the file exists but has no parseable checks.
    """
    eval_path = skill_dir / "EVAL.md"
    if not eval_path.exists():
        return None
    try:
        content = eval_path.read_text(encoding="utf-8")
    except OSError as exc:
        _logger.warning("Failed to read %s: %s", eval_path, exc)
        return None
    return parse_eval_md(content)


def run_eval(
    skill_name: str,
    checks: list[EvalCheck],
    skill_output: str,
    evaluator: Evaluator,
) -> SkillEvalResult:
    """Run all checks against *skill_output* using *evaluator*.

    The evaluator callable receives ``(check_text, skill_output)`` and
    returns ``"pass"``, ``"fail"``, ``"skip"``, or any other string
    (treated as ``"error"``).
    """
    result = SkillEvalResult(skill_name=skill_name)
    for check in checks:
        try:
            raw_status = evaluator(check.text, skill_output)
            status = _normalize_status(raw_status)
            detail = raw_status if status == CheckStatus.ERROR else ""
        except Exception as exc:
            status = CheckStatus.ERROR
            detail = str(exc)
            _logger.exception("Eval check failed: %s", check.text)
        result.checks.append(CheckResult(check=check, status=status, detail=detail))
    return result


def _normalize_status(raw: str) -> CheckStatus:
    """Normalize an evaluator's string return to a :class:`CheckStatus`."""
    lowered = raw.strip().lower()
    if lowered in ("pass", "passed", "yes", "true", "ok"):
        return CheckStatus.PASS
    if lowered in ("fail", "failed", "no", "false"):
        return CheckStatus.FAIL
    if lowered in ("skip", "skipped", "n/a", "na", "not applicable"):
        return CheckStatus.SKIP
    return CheckStatus.ERROR


def has_eval(skill_dir: Path) -> bool:
    """Return ``True`` if the skill directory has an ``EVAL.md`` file."""
    return (skill_dir / "EVAL.md").exists()


def eval_skill_output(
    skill_dir: Path,
    skill_output: str,
    evaluator: Evaluator,
) -> SkillEvalResult | None:
    """Convenience: load EVAL.md from *skill_dir* and run against output.

    Returns ``None`` if the skill has no ``EVAL.md``.
    """
    checks = load_eval_file(skill_dir)
    if checks is None:
        return None
    if not checks:
        _logger.warning("EVAL.md for %s has no parseable checks", skill_dir.name)
    skill_name = skill_dir.name
    return run_eval(skill_name, checks, skill_output, evaluator)
