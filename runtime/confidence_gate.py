#!/usr/bin/env python3
"""Evidence-weighted confidence gate (CONF-W1).

Inspired by GUARDRAILS_AI's FailResult.error_spans (evidence with weights)
and NeMo Guardrails' RailOutcome (decision + metadata).

The confidence gate evaluates action responses and computes a confidence
score based on weighted evidence. If the score falls below a threshold,
the gate blocks the action (fail-closed).

Evidence sources (each weighted 0.0-1.0):
- Gate verdict: did a gate block/deny? (weight: 0.4)
- Test result: did tests pass? (weight: 0.3)
- Lint result: did lint pass? (weight: 0.15)
- Type check: did mypy pass? (weight: 0.15)

Usage::

    from runtime.confidence_gate import ConfidenceGate, Evidence
    gate = ConfidenceGate(threshold=0.7)
    gate.add_evidence(Evidence("gate_verdict", True, 0.4, "probity allowed"))
    gate.add_evidence(Evidence("test_result", True, 0.3, "all tests passed"))
    verdict = gate.evaluate()
    if not verdict.confident:
        print(f"Low confidence: {verdict.score} — {verdict.reason}")
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ConfidenceLevel(str, Enum):
    """Confidence levels mapped from score ranges."""

    HIGH = "high"  # score >= 0.8
    MEDIUM = "medium"  # 0.5 <= score < 0.8
    LOW = "low"  # 0.2 <= score < 0.5
    CRITICAL = "critical"  # score < 0.2


@dataclass
class Evidence:
    """A single piece of evidence for confidence scoring.

    Attributes:
        source: Where the evidence came from (e.g. "gate_verdict", "test_result").
        passed: Whether this evidence source passed (True) or failed (False).
        weight: How much this evidence counts (0.0-1.0). All weights should
            sum to 1.0 across all evidence sources.
        detail: Human-readable explanation.
    """

    source: str
    passed: bool
    weight: float
    detail: str = ""

    def __post_init__(self) -> None:
        if not 0.0 <= self.weight <= 1.0:
            raise ValueError(f"Evidence weight must be between 0.0 and 1.0, got {self.weight}")


@dataclass(frozen=True)
class ConfidenceVerdict:
    """Result of confidence gate evaluation.

    Attributes:
        score: Weighted confidence score (0.0-1.0).
        confident: Whether the score meets the threshold.
        level: Confidence level (HIGH/MEDIUM/LOW/CRITICAL).
        reason: Human-readable explanation.
        evidence: List of evidence that contributed to the score.
    """

    score: float
    confident: bool
    level: ConfidenceLevel
    reason: str
    evidence: tuple[Evidence, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": round(self.score, 4),
            "confident": self.confident,
            "level": self.level.value,
            "reason": self.reason,
            "evidence": [
                {"source": e.source, "passed": e.passed, "weight": e.weight, "detail": e.detail}
                for e in self.evidence
            ],
        }


class ConfidenceGate:
    """Evidence-weighted confidence gate (CONF-W1).

    Collects evidence from multiple sources and computes a weighted
    confidence score. If the score is below the threshold, the gate
    blocks the action (fail-closed).
    """

    def __init__(self, threshold: float = 0.7, *, normalize: bool = False) -> None:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(f"threshold must be in [0, 1], got {threshold}")
        self.threshold = threshold
        self._normalize = normalize
        self._evidence: list[Evidence] = []

    def add_evidence(self, evidence: Evidence) -> None:
        """Add a piece of evidence to the gate."""
        if not 0.0 <= evidence.weight <= 1.0:
            raise ValueError(f"Evidence weight must be between 0.0 and 1.0, got {evidence.weight}")
        self._evidence.append(evidence)

    def add_evidence_simple(self, source: str, passed: bool, weight: float, detail: str = "") -> None:
        """Convenience: add evidence without constructing an Evidence object."""
        if not 0.0 <= weight <= 1.0:
            raise ValueError(f"Evidence weight must be between 0.0 and 1.0, got {weight}")
        self._evidence.append(Evidence(source=source, passed=passed, weight=weight, detail=detail))

    @property
    def total_weight(self) -> float:
        """Sum of all evidence weights."""
        return sum(e.weight for e in self._evidence)

    def evaluate(self) -> ConfidenceVerdict:
        """Evaluate the confidence gate. Returns a ConfidenceVerdict."""
        if not self._evidence:
            return ConfidenceVerdict(
                score=0.0,
                confident=False,
                level=ConfidenceLevel.CRITICAL,
                reason="No evidence provided — fail-closed",
                evidence=(),
            )
        # Normalize weights in case they don't sum to 1.0
        total = self.total_weight
        if total == 0:
            return ConfidenceVerdict(
                score=0.0,
                confident=False,
                level=ConfidenceLevel.CRITICAL,
                reason="Total evidence weight is zero",
                evidence=tuple(self._evidence),
            )
        if not self._normalize and abs(total - 1.0) > 1e-9:
            raise ValueError(
                f"Evidence weights must sum to 1.0, got {total}; "
                "pass normalize=True to auto-normalize"
            )
        # Compute weighted score: sum(passed * weight) / total_weight
        score = sum((1.0 if e.passed else 0.0) * e.weight for e in self._evidence) / total
        # Determine level
        if score >= 0.8:
            level = ConfidenceLevel.HIGH
        elif score >= 0.5:
            level = ConfidenceLevel.MEDIUM
        elif score >= 0.2:
            level = ConfidenceLevel.LOW
        else:
            level = ConfidenceLevel.CRITICAL
        # Determine confidence
        confident = score >= self.threshold
        # Build reason
        failed = [e.source for e in self._evidence if not e.passed]
        if failed:
            reason = f"Failed evidence: {', '.join(failed)} (score: {score:.2f})"
        else:
            reason = f"All evidence passed (score: {score:.2f})"
        return ConfidenceVerdict(
            score=score,
            confident=confident,
            level=level,
            reason=reason,
            evidence=tuple(self._evidence),
        )

    def reset(self) -> None:
        """Clear all evidence."""
        self._evidence.clear()
