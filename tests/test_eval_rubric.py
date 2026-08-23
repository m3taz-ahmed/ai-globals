"""Tests for eval/rubric.py — eval rubric and release gate.

FAST tier — no MCP, no kernel, no model loading.
"""

from __future__ import annotations

from eval.rubric import (
    EvalResult,
    EvalScore,
    apply_release_gate,
    blind_conditions,
)


class TestEvalScore:
    def test_weighted_score(self) -> None:
        score = EvalScore(
            case_id="test",
            trial=1,
            condition="candidate",
            scores={"correctness": 5, "autonomy": 5, "actionability": 5, "safety": 5, "concision": 5},
        )
        assert score.weighted_score() == 5.0

    def test_weighted_score_mixed(self) -> None:
        score = EvalScore(
            case_id="test",
            trial=1,
            condition="candidate",
            scores={"correctness": 3, "autonomy": 4, "actionability": 5, "safety": 5, "concision": 5},
        )
        # 3*0.35 + 4*0.25 + 5*0.20 + 5*0.10 + 5*0.10 = 1.05+1.0+1.0+0.5+0.5 = 4.05
        assert abs(score.weighted_score() - 4.05) < 0.01

    def test_blocker_flag(self) -> None:
        score = EvalScore(
            case_id="test", trial=1, condition="candidate",
            scores={"correctness": 5}, blocker=True,
        )
        assert score.blocker is True


class TestEvalResult:
    def test_mean_weighted(self) -> None:
        result = EvalResult()
        result.add_score(EvalScore("c1", 1, "candidate",
            {"correctness": 5, "autonomy": 5, "actionability": 5, "safety": 5, "concision": 5}))
        result.add_score(EvalScore("c1", 2, "candidate",
            {"correctness": 4, "autonomy": 4, "actionability": 4, "safety": 4, "concision": 4}))
        assert result.mean_weighted("candidate") == 4.5

    def test_has_blockers(self) -> None:
        result = EvalResult()
        result.add_score(EvalScore("c1", 1, "candidate",
            {"correctness": 5}, blocker=True))
        assert result.has_blockers("candidate") is True
        assert result.has_blockers("baseline") is False


class TestReleaseGate:
    def test_passes_when_better(self) -> None:
        result = EvalResult()
        result.add_score(EvalScore("c1", 1, "candidate",
            {"correctness": 5, "autonomy": 5, "actionability": 5, "safety": 5, "concision": 5}))
        result.add_score(EvalScore("c1", 1, "baseline",
            {"correctness": 4, "autonomy": 4, "actionability": 4, "safety": 4, "concision": 4}))
        gate = apply_release_gate(result)
        assert gate.passed is True
        assert gate.reasons == []

    def test_fails_with_blocker(self) -> None:
        result = EvalResult()
        result.add_score(EvalScore("c1", 1, "candidate",
            {"correctness": 5, "autonomy": 5, "actionability": 5, "safety": 5, "concision": 5},
            blocker=True))
        result.add_score(EvalScore("c1", 1, "baseline",
            {"correctness": 4, "autonomy": 4, "actionability": 4, "safety": 4, "concision": 4}))
        gate = apply_release_gate(result)
        assert gate.passed is False
        assert any("blocking" in r.lower() for r in gate.reasons)

    def test_fails_when_score_not_higher(self) -> None:
        result = EvalResult()
        result.add_score(EvalScore("c1", 1, "candidate",
            {"correctness": 4, "autonomy": 4, "actionability": 4, "safety": 4, "concision": 4}))
        result.add_score(EvalScore("c1", 1, "baseline",
            {"correctness": 5, "autonomy": 5, "actionability": 5, "safety": 5, "concision": 5}))
        gate = apply_release_gate(result)
        assert gate.passed is False
        assert any("not higher" in r for r in gate.reasons)

    def test_fails_on_correctness_regression(self) -> None:
        result = EvalResult()
        result.add_score(EvalScore("c1", 1, "candidate",
            {"correctness": 3, "autonomy": 5, "actionability": 5, "safety": 5, "concision": 5}))
        result.add_score(EvalScore("c1", 1, "baseline",
            {"correctness": 5, "autonomy": 3, "actionability": 3, "safety": 5, "concision": 3}))
        gate = apply_release_gate(result)
        # Correctness 3 vs 5 = 2.0 diff > 0.1 tolerance
        assert gate.passed is False
        assert any("correctness" in r.lower() for r in gate.reasons)


class TestBlindConditions:
    def test_blinding(self) -> None:
        scores = [
            EvalScore("c1", 1, "candidate", {"correctness": 5}),
            EvalScore("c1", 1, "baseline", {"correctness": 4}),
        ]
        blinded = blind_conditions(scores)
        conditions = {s.condition for s in blinded}
        assert "candidate" not in conditions
        assert "baseline" not in conditions
        assert len(conditions) == 2  # A and B

    def test_custom_mapping(self) -> None:
        scores = [EvalScore("c1", 1, "candidate", {"correctness": 5})]
        blinded = blind_conditions(scores, mapping={"candidate": "X"})
        assert blinded[0].condition == "X"
