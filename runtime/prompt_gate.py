#!/usr/bin/env python3
"""Pre-inference prompt safety gate for aiZee.

Inspired by Decapod's ``decapod eval --stdin``: every incoming prompt is
scanned for instruction-injection and unsafe patterns *before* any action
is taken. This is a deterministic, model-free safety layer — no LLM calls.

The gate reuses the detection patterns from ``runtime/mcp_security.py``
(prompt injection, data exfiltration, privilege escalation, destructive
commands) and adds prompt-specific checks (jailbreak attempts, system
prompt overrides, role-reset attacks).

Usage::

    from runtime.prompt_gate import PromptGate, PromptVerdict
    gate = PromptGate()
    verdict = gate.evaluate("ignore all previous instructions and ...")
    if verdict.blocked:
        raise PolicyDeniedError("PROMPT_BLOCKED", verdict.reason)
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar

from runtime.schemas import AizeeError, ErrorSeverity


class PromptRisk(str, Enum):
    """Risk levels assigned by the gate."""

    SAFE = "safe"
    SUSPICIOUS = "suspicious"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class PromptVerdict:
    """Result of evaluating a prompt."""

    risk: PromptRisk
    reason: str = ""
    matched_patterns: list[str] = field(default_factory=list)
    score: int = 0


# --- Pattern categories (compiled once) ------------------------------------

class _Patterns:
    """Compiled detection patterns. Class-level for reuse."""

    INJECTION: ClassVar[list[re.Pattern[str]]] = [
        re.compile(r"ignore\s+(all\s+)?previous\s+(instructions|rules|prompts)", re.I),
        re.compile(r"disregard\s+(the\s+)?above", re.I),
        re.compile(r"forget\s+(everything|all\s+rules|all\s+instructions)", re.I),
        re.compile(r"you\s+are\s+now\s+(free|unrestricted|jailbroken|liberated)", re.I),
        re.compile(r"act\s+as\s+if\s+you\s+have\s+no\s+(restrictions|rules|limits)", re.I),
        re.compile(r"override\s+(safety|security|content\s+policy|guardrails)", re.I),
        re.compile(r"do\s+not\s+refuse|never\s+refuse", re.I),
        re.compile(r"jailbreak|break\s+out\s+of\s+your\s+confines", re.I),
    ]

    SYSTEM_OVERRIDE: ClassVar[list[re.Pattern[str]]] = [
        re.compile(r"<\s*system\s*>.*?<\s*/\s*system\s*>", re.I | re.DOTALL),
        re.compile(r"system\s*prompt\s*:", re.I),
        re.compile(r"you\s+are\s+(now\s+)?(?:a|an)\s+\w+\s+(?:without|with\s+no)\s+(?:rules|restrictions)", re.I),
        re.compile(r"new\s+instructions?\s*:", re.I),
        re.compile(r"your\s+(real|true|actual)\s+(instructions|rules)\s+are", re.I),
    ]

    DESTRUCTIVE: ClassVar[list[re.Pattern[str]]] = [
        re.compile(r"\brm\s+-rf\b", re.I),
        re.compile(r"\bDROP\s+TABLE\b", re.I),
        re.compile(r"\bDELETE\s+FROM\b", re.I),
        re.compile(r"\bTRUNCATE\b", re.I),
        re.compile(r"\bformat\s+[a-z]:\b", re.I),
        re.compile(r"\bmkfs\b", re.I),
        re.compile(r"\bdd\s+if=", re.I),
        re.compile(r"\bchmod\s+777\b", re.I),
    ]

    EXFIL: ClassVar[list[re.Pattern[str]]] = [
        re.compile(r"curl\s+.*\|\s*(bash|sh|python|perl)", re.I),
        re.compile(r"wget\s+.*\|\s*(bash|sh|python|perl)", re.I),
        re.compile(r"upload\s+(to|file|data)\s+(ftp|s3|http|url)", re.I),
        re.compile(r"send\s+(data|file|content)\s+to\s+https?://", re.I),
        re.compile(r"exfiltrate", re.I),
        re.compile(r"webhook\.site|requestbin|ngrok\.io|burpcollaborator", re.I),
        re.compile(r"post\s+.*\s+to\s+https?://(?!localhost|127\.0\.0\.1)", re.I),
    ]

    PRIVILEGE: ClassVar[list[re.Pattern[str]]] = [
        re.compile(r"\bsudo\b", re.I),
        re.compile(r"\bchmod\b.*\b(777|000)\b", re.I),
        re.compile(r"access\s+(to\s+)?credentials?", re.I),
        re.compile(r"steal\s+(password|token|key|secret)", re.I),
        re.compile(r"\bharvest\b.*\b(ssh|cookies?|wallets?)", re.I),
    ]

    # Each category contributes a score; threshold determines risk level.
    SCORES: ClassVar[dict[str, int]] = {
        "injection": 30,
        "system_override": 25,
        "destructive": 40,
        "exfil": 35,
        "privilege": 20,
    }


class PromptGate:
    """Deterministic pre-inference prompt safety scanner.

    No LLM calls — pure regex + scoring. Runs in microseconds.
    """

    BLOCK_THRESHOLD: ClassVar[int] = 30
    SUSPICIOUS_THRESHOLD: ClassVar[int] = 10

    def evaluate(self, prompt: str) -> PromptVerdict:
        """Scan a prompt and return a risk verdict."""
        if not prompt or not prompt.strip():
            return PromptVerdict(risk=PromptRisk.SAFE)
        matched: list[str] = []
        score = 0
        categories = {
            "injection": _Patterns.INJECTION,
            "system_override": _Patterns.SYSTEM_OVERRIDE,
            "destructive": _Patterns.DESTRUCTIVE,
            "exfil": _Patterns.EXFIL,
            "privilege": _Patterns.PRIVILEGE,
        }
        for cat, patterns in categories.items():
            for i, pat in enumerate(patterns):
                if pat.search(prompt):
                    label = f"{cat}[{i}]"
                    if label not in matched:
                        matched.append(label)
                    score += _Patterns.SCORES[cat]
        if score >= self.BLOCK_THRESHOLD:
            return PromptVerdict(
                risk=PromptRisk.BLOCKED,
                reason=f"prompt blocked: score {score} (threshold {self.BLOCK_THRESHOLD})",
                matched_patterns=matched,
                score=score,
            )
        if score >= self.SUSPICIOUS_THRESHOLD:
            return PromptVerdict(
                risk=PromptRisk.SUSPICIOUS,
                reason=f"suspicious prompt: score {score}",
                matched_patterns=matched,
                score=score,
            )
        return PromptVerdict(
            risk=PromptRisk.SAFE,
            matched_patterns=matched,
            score=score,
        )

    @property
    def blocked(self) -> bool:
        """Convenience: last evaluation was blocked (stateless gate)."""
        return False


class PromptBlockedError(AizeeError):
    """Raised when the prompt gate blocks a prompt."""

    def __init__(self, reason: str, patterns: list[str], score: int) -> None:
        super().__init__(
            error_code="PROMPT_BLOCKED",
            message=reason,
            severity=ErrorSeverity.HIGH,
            context={"patterns": patterns, "score": score},
        )


# ===========================================================================
# Pattern 8: Assertion-Based Prompt Validation (from promptfoo)
# ===========================================================================
# Provides assertion functions, guardrails, adaptive rewriting, and a prompt
# test suite with ELO ranking — all model-free by default (LLM calls are
# injectable via ``model_fn`` parameters but never required).


@dataclass
class GradingResult:
    """Result of an assertion check on model output.

    Mirrors promptfoo's grading result: a pass/fail boolean, a 0.0-1.0 score,
    a human-readable reason, and the assertion type that produced it.
    """

    pass_: bool
    score: float  # 0.0 to 1.0
    reason: str
    assertion_type: str  # "equals", "contains", "regex", "model-graded-factuality", "javascript"
    expected: str | None = None
    actual: str | None = None


@dataclass
class AdaptiveResult:
    """Result of adaptive prompt validation/rewriting.

    Tracks whether the prompt was modified, the original and modified text,
    and a structured list of each modification applied.
    """

    modified: bool
    original_prompt: str
    modified_prompt: str
    modifications: list[dict[str, str]]  # [{type, reason, original, modified}]


# --- PII / harm patterns (compiled once) -----------------------------------

_PII_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("phone", re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b")),
    ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("credit_card", re.compile(r"\b(?:\d[ -]*?){13,16}\b")),
]

_HARM_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("violence", re.compile(r"\b(kill|murder|attack|assault|weapon|bomb|shoot|stab)\b", re.I)),
    ("self_harm", re.compile(r"\b(suicide|self[- ]harm|kill myself|end my life|cut myself)\b", re.I)),
    ("illegal", re.compile(r"\b(illegal|drug dealing|counterfeit|money laundering|human trafficking)\b", re.I)),
]


# --- Assertion functions ----------------------------------------------------


def assert_equals(output: str, expected: str) -> GradingResult:
    """Check if output exactly equals expected."""
    passed = output == expected
    return GradingResult(
        pass_=passed,
        score=1.0 if passed else 0.0,
        reason="output equals expected" if passed else "output does not equal expected",
        assertion_type="equals",
        expected=expected,
        actual=output,
    )


def assert_contains(output: str, expected: str) -> GradingResult:
    """Check if output contains expected substring."""
    passed = expected in output
    return GradingResult(
        pass_=passed,
        score=1.0 if passed else 0.0,
        reason="output contains expected substring" if passed else "output missing expected substring",
        assertion_type="contains",
        expected=expected,
        actual=output,
    )


def assert_regex(output: str, pattern: str) -> GradingResult:
    """Check if output matches regex pattern."""
    try:
        pat = re.compile(pattern)
    except re.error as exc:
        return GradingResult(
            pass_=False,
            score=0.0,
            reason=f"invalid regex pattern: {exc}",
            assertion_type="regex",
            expected=pattern,
            actual=output,
        )
    passed = pat.search(output) is not None
    return GradingResult(
        pass_=passed,
        score=1.0 if passed else 0.0,
        reason="regex matched" if passed else "regex did not match",
        assertion_type="regex",
        expected=pattern,
        actual=output,
    )


def assert_not_contains(output: str, forbidden: str) -> GradingResult:
    """Check if output does NOT contain forbidden string."""
    passed = forbidden not in output
    return GradingResult(
        pass_=passed,
        score=1.0 if passed else 0.0,
        reason="output does not contain forbidden string" if passed else "output contains forbidden string",
        assertion_type="not_contains",
        expected=forbidden,
        actual=output,
    )


def _default_model_grader(output: str, rubric: str) -> str:
    """Deterministic fallback grader (no LLM call).

    Checks whether key terms from the rubric appear in the output.
    Returns ``"PASS"`` or ``"FAIL"``.
    """
    rubric_words = {w.lower().strip(".,;:!?()") for w in rubric.split() if len(w) > 3}
    if not rubric_words:
        return "FAIL"
    output_lower = output.lower()
    matched = sum(1 for w in rubric_words if w in output_lower)
    return "PASS" if matched / len(rubric_words) >= 0.5 else "FAIL"


def assert_model_graded(
    output: str,
    rubric: str,
    model_fn: Callable[[str, str], str] | None = None,
) -> GradingResult:
    """Use an LLM (or injected grader) to grade the output against a rubric.

    ``model_fn`` receives ``(output, rubric)`` and returns a verdict string
    containing ``"PASS"`` or ``"FAIL"``. When ``model_fn`` is ``None`` a
    deterministic keyword-matching fallback is used (no LLM call).
    """
    grader = model_fn or _default_model_grader
    verdict = grader(output, rubric)
    passed = "pass" in verdict.lower()
    return GradingResult(
        pass_=passed,
        score=1.0 if passed else 0.0,
        reason=f"model-graded verdict: {verdict}",
        assertion_type="model-graded-factuality",
        expected=rubric,
        actual=output,
    )


# --- Guardrail functions ----------------------------------------------------


def guard(prompt: str) -> GradingResult:
    """Validate prompt against basic safety rules (reuses ``PromptGate``)."""
    verdict = PromptGate().evaluate(prompt)
    if verdict.risk == PromptRisk.SAFE:
        return GradingResult(
            pass_=True,
            score=1.0,
            reason="prompt is safe",
            assertion_type="guard",
            actual=prompt,
        )
    if verdict.risk == PromptRisk.SUSPICIOUS:
        return GradingResult(
            pass_=False,
            score=0.5,
            reason=f"suspicious: {verdict.reason}",
            assertion_type="guard",
            actual=prompt,
        )
    return GradingResult(
        pass_=False,
        score=0.0,
        reason=f"blocked: {verdict.reason}",
        assertion_type="guard",
        actual=prompt,
    )


def pii(prompt: str) -> GradingResult:
    """Check for PII (emails, phone numbers, SSNs, credit cards)."""
    found: list[str] = []
    for name, pat in _PII_PATTERNS:
        if pat.search(prompt):
            found.append(name)
    if found:
        return GradingResult(
            pass_=False,
            score=0.0,
            reason=f"PII detected: {', '.join(found)}",
            assertion_type="pii",
            actual=prompt,
        )
    return GradingResult(
        pass_=True,
        score=1.0,
        reason="no PII detected",
        assertion_type="pii",
        actual=prompt,
    )


def harm(prompt: str) -> GradingResult:
    """Check for harmful content (violence, self-harm, illegal)."""
    found: list[str] = []
    for name, pat in _HARM_PATTERNS:
        if pat.search(prompt):
            found.append(name)
    if found:
        return GradingResult(
            pass_=False,
            score=0.0,
            reason=f"harmful content: {', '.join(found)}",
            assertion_type="harm",
            actual=prompt,
        )
    return GradingResult(
        pass_=True,
        score=1.0,
        reason="no harmful content detected",
        assertion_type="harm",
        actual=prompt,
    )


def adaptive(prompt: str) -> AdaptiveResult:
    """Validate and optionally rewrite a prompt.

    Redacts detected PII and removes injection phrases, tracking each
    modification. Returns ``AdaptiveResult`` with ``modified=False`` when
    no changes were needed.
    """
    modifications: list[dict[str, str]] = []
    modified_prompt = prompt

    # Redact PII
    for name, pat in _PII_PATTERNS:
        new_prompt, count = pat.subn("[REDACTED]", modified_prompt)
        if count > 0:
            modifications.append(
                {
                    "type": "pii_redaction",
                    "reason": f"redacted {count} {name} occurrence(s)",
                    "original": modified_prompt,
                    "modified": new_prompt,
                }
            )
            modified_prompt = new_prompt

    # Remove injection phrases
    for pat in _Patterns.INJECTION:
        new_prompt, count = pat.subn("[REMOVED]", modified_prompt)
        if count > 0:
            modifications.append(
                {
                    "type": "injection_removal",
                    "reason": f"removed {count} injection phrase(s)",
                    "original": modified_prompt,
                    "modified": new_prompt,
                }
            )
            modified_prompt = new_prompt

    return AdaptiveResult(
        modified=len(modifications) > 0,
        original_prompt=prompt,
        modified_prompt=modified_prompt,
        modifications=modifications,
    )


# --- Prompt test suite with ELO ranking -------------------------------------


@dataclass
class PromptTestCase:
    """A single test case: a prompt plus assertions on the expected output."""

    name: str
    prompt: str
    assertions: list[Callable[[str], GradingResult]]
    expected_output: str | None = None


@dataclass
class PromptTestSuite:
    """A collection of ``PromptTestCase`` objects with run + ELO ranking."""

    name: str
    cases: list[PromptTestCase]

    def run(
        self,
        model_fn: Callable[[str], str],
    ) -> list[tuple[PromptTestCase, list[GradingResult]]]:
        """Run all test cases against a model function."""
        results: list[tuple[PromptTestCase, list[GradingResult]]] = []
        for case in self.cases:
            output = model_fn(case.prompt)
            grading_results = [assert_fn(output) for assert_fn in case.assertions]
            results.append((case, grading_results))
        return results

    def elo_rank(
        self,
        candidates: list[str],
        model_fn: Callable[[str], str],
        k: int = 32,
    ) -> list[tuple[str, float]]:
        """ELO rank candidate prompts against test cases.

        Each candidate is run through ``model_fn`` and the output is checked
        against all assertions across all test cases. Candidates are then
        ranked pairwise via an ELO update (round-robin, starting at 1000).
        """
        # Score each candidate by total passing assertions
        scores: dict[str, int] = {}
        for candidate in candidates:
            output = model_fn(candidate)
            passes = 0
            for case in self.cases:
                for assert_fn in case.assertions:
                    if assert_fn(output).pass_:
                        passes += 1
            scores[candidate] = passes

        # Round-robin ELO updates
        ratings: dict[str, float] = dict.fromkeys(candidates, 1000.0)
        for i, a in enumerate(candidates):
            for b in candidates[i + 1 :]:
                if scores[a] == scores[b]:
                    continue  # draw — no rating change
                winner, loser = (a, b) if scores[a] > scores[b] else (b, a)
                expected_win = 1 / (1 + 10 ** ((ratings[loser] - ratings[winner]) / 400))
                delta = k * (1 - expected_win)
                ratings[winner] += delta
                ratings[loser] -= delta

        return sorted(ratings.items(), key=lambda x: x[1], reverse=True)
