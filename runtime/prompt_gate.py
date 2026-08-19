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
