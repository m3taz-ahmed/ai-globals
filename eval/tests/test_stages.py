"""Tests for eval/stages.py — 3-Stage Evaluation Gate."""

from __future__ import annotations

from eval.stages import EvaluationGate, StageName


class TestEvaluationGate:
    def test_all_stages_pass(self) -> None:
        gate = EvaluationGate()
        gate.run_all(
            checks={"ruff": True, "mypy": True},
            review_notes="Good",
            approved=True,
            model_verdicts=[{"model": "a", "verdict": "pass"}, {"model": "b", "verdict": "pass"}],
        )
        assert gate.all_stages_passed is True

    def test_mechanical_failure_stops(self) -> None:
        gate = EvaluationGate()
        results = gate.run_all(
            checks={"ruff": False},
            review_notes="",
            approved=True,
            model_verdicts=[],
        )
        assert len(results) == 1
        assert results[0].stage == StageName.MECHANICAL

    def test_semantic_failure_stops(self) -> None:
        gate = EvaluationGate()
        results = gate.run_all(
            checks={"ruff": True},
            review_notes="Bad",
            approved=False,
            model_verdicts=[],
        )
        assert len(results) == 2
        assert results[1].passed is False

    def test_consensus_majority_passes(self) -> None:
        gate = EvaluationGate()
        gate.run_mechanical({"ruff": True})
        gate.run_semantic("ok", approved=True)
        gate.run_consensus([{"verdict": "pass"}, {"verdict": "fail"}, {"verdict": "pass"}])
        assert gate.all_stages_passed is True

    def test_consensus_no_majority_fails(self) -> None:
        gate = EvaluationGate()
        gate.run_mechanical({"ruff": True})
        gate.run_semantic("ok", approved=True)
        gate.run_consensus([{"verdict": "fail"}, {"verdict": "fail"}, {"verdict": "pass"}])
        assert gate.all_stages_passed is False

    def test_consensus_empty_fails(self) -> None:
        gate = EvaluationGate()
        gate.run_mechanical({"ruff": True})
        gate.run_semantic("ok", approved=True)
        result = gate.run_consensus([])
        assert result.passed is False

    def test_to_dict(self) -> None:
        gate = EvaluationGate()
        gate.run_all(
            checks={"ruff": True},
            review_notes="ok",
            approved=True,
            model_verdicts=[{"verdict": "pass"}],
        )
        d = gate.to_dict()
        assert len(d) == 3
        assert all("stage" in item for item in d)
