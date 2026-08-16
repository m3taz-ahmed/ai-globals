#!/usr/bin/env python3
"""3-Stage Evaluation Gate — progressive verification (from ouroboros).

Three-stage verification:
1. Mechanical (free) — Automated checks (lint, types, tests)
2. Semantic — Human-in-the-loop review
3. Consensus — Multi-model cross-verification

Usage::

    from eval.stages import EvaluationGate, StageResult

    gate = EvaluationGate()
    gate.run_mechanical({"ruff": True, "mypy": True, "pytest": True})
    gate.run_semantic(review_notes="Looks good")
    gate.run_consensus([{"model": "gpt-4", "verdict": "pass"}])
    assert gate.all_stages_passed
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StageName(str, Enum):
    """Three evaluation stages (from ouroboros)."""

    MECHANICAL = "mechanical"  # Automated checks (free)
    SEMANTIC = "semantic"      # Human-in-the-loop review
    CONSENSUS = "consensus"    # Multi-model cross-verification


@dataclass
class StageResult:
    """Result of a single evaluation stage."""

    stage: StageName
    passed: bool
    details: dict[str, Any] = field(default_factory=dict)
    notes: str = ""


@dataclass
class EvaluationGate:
    """3-Stage Evaluation Gate (from ouroboros).

    Progressive verification: Mechanical → Semantic → Consensus.
    Each stage must pass before the next is evaluated.
    """

    results: list[StageResult] = field(default_factory=list)

    def run_mechanical(self, checks: dict[str, bool]) -> StageResult:
        """Stage 1: Automated checks (free, no LLM needed)."""
        failed = [k for k, v in checks.items() if not v]
        result = StageResult(
            stage=StageName.MECHANICAL,
            passed=len(failed) == 0,
            details={"checks": checks, "failed": failed},
            notes=f"{len(checks) - len(failed)}/{len(checks)} automated checks passed",
        )
        self.results.append(result)
        return result

    def run_semantic(self, review_notes: str, approved: bool = True) -> StageResult:
        """Stage 2: Human-in-the-loop semantic review."""
        result = StageResult(
            stage=StageName.SEMANTIC,
            passed=approved,
            notes=review_notes,
        )
        self.results.append(result)
        return result

    def run_consensus(self, model_verdicts: list[dict[str, Any]]) -> StageResult:
        """Stage 3: Multi-model consensus verification."""
        if not model_verdicts:
            result = StageResult(
                stage=StageName.CONSENSUS,
                passed=False,
                notes="No model verdicts provided",
            )
        else:
            passes = sum(1 for v in model_verdicts if v.get("verdict") == "pass")
            passed = passes >= len(model_verdicts) // 2 + 1  # Majority
            result = StageResult(
                stage=StageName.CONSENSUS,
                passed=passed,
                details={"verdicts": model_verdicts, "passes": passes},
                notes=f"{passes}/{len(model_verdicts)} models agree",
            )
        self.results.append(result)
        return result

    def run_all(
        self,
        checks: dict[str, bool],
        review_notes: str,
        approved: bool,
        model_verdicts: list[dict[str, Any]],
    ) -> list[StageResult]:
        """Run all 3 stages in sequence. Stops on first failure."""
        self.results = []
        r1 = self.run_mechanical(checks)
        if not r1.passed:
            return self.results
        r2 = self.run_semantic(review_notes, approved)
        if not r2.passed:
            return self.results
        self.run_consensus(model_verdicts)
        return self.results

    @property
    def all_stages_passed(self) -> bool:
        return len(self.results) == 3 and all(r.passed for r in self.results)

    def to_dict(self) -> list[dict[str, Any]]:
        return [
            {"stage": r.stage.value, "passed": r.passed, "notes": r.notes}
            for r in self.results
        ]


if __name__ == "__main__":
    gate = EvaluationGate()
    gate.run_all(
        checks={"ruff": True, "mypy": True, "pytest": True},
        review_notes="Code looks good",
        approved=True,
        model_verdicts=[{"model": "gpt-4", "verdict": "pass"},
                        {"model": "claude", "verdict": "pass"}],
    )
    print(f"All passed: {gate.all_stages_passed}")
