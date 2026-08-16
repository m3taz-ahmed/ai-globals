"""Tests for eval/harness.py — Evidence-Based Gates (5-gate verification)."""

from __future__ import annotations

from eval.harness import EvidenceGates, GateName, GateResult


class TestEvidenceGates:
    """Tests for the 5-gate evidence-based verification sequence."""

    def test_all_gates_pass(self) -> None:
        gates = EvidenceGates()
        results = gates.run_all(
            scope_items=["feat-a", "feat-b"],
            quality_checks={"ruff": True, "mypy": True, "pytest": True},
            evidence_commands=["ruff check .", "pytest -q"],
            rollback_strategy="git revert <commit>",
            summary="Implemented feature A with tests",
        )
        assert len(results) == 5
        assert gates.all_passed is True

    def test_scope_gate_fails_on_empty(self) -> None:
        gates = EvidenceGates()
        results = gates.run_all(
            scope_items=[],
            quality_checks={"ruff": True},
            evidence_commands=["cmd"],
            rollback_strategy="revert",
            summary="summary",
        )
        assert len(results) == 1
        assert results[0].name == GateName.SCOPE
        assert results[0].passed is False

    def test_quality_gate_fails_on_failed_check(self) -> None:
        gates = EvidenceGates()
        results = gates.run_all(
            scope_items=["feat-a"],
            quality_checks={"ruff": True, "mypy": False},
            evidence_commands=["cmd"],
            rollback_strategy="revert",
            summary="summary",
        )
        assert len(results) == 2
        assert results[1].name == GateName.QUALITY
        assert results[1].passed is False
        assert gates.all_passed is False

    def test_evidence_gate_fails_on_empty(self) -> None:
        gates = EvidenceGates()
        results = gates.run_all(
            scope_items=["feat-a"],
            quality_checks={"ruff": True},
            evidence_commands=[],
            rollback_strategy="revert",
            summary="summary",
        )
        assert len(results) == 3
        assert results[2].name == GateName.EVIDENCE
        assert results[2].passed is False

    def test_risk_gate_fails_on_empty_strategy(self) -> None:
        gates = EvidenceGates()
        results = gates.run_all(
            scope_items=["feat-a"],
            quality_checks={"ruff": True},
            evidence_commands=["cmd"],
            rollback_strategy="",
            summary="summary",
        )
        assert len(results) == 4
        assert results[3].name == GateName.RISK
        assert results[3].passed is False

    def test_communication_gate_fails_on_empty(self) -> None:
        gates = EvidenceGates()
        results = gates.run_all(
            scope_items=["feat-a"],
            quality_checks={"ruff": True},
            evidence_commands=["cmd"],
            rollback_strategy="revert",
            summary="",
        )
        assert len(results) == 5
        assert results[4].name == GateName.COMMUNICATION
        assert results[4].passed is False

    def test_to_dict_serialization(self) -> None:
        gates = EvidenceGates()
        gates.run_all(
            scope_items=["feat-a"],
            quality_checks={"ruff": True},
            evidence_commands=["cmd"],
            rollback_strategy="revert",
            summary="done",
        )
        d = gates.to_dict()
        assert len(d) == 5
        assert all("name" in item and "passed" in item for item in d)

    def test_gate_order_is_correct(self) -> None:
        gates = EvidenceGates()
        gates.run_all(
            scope_items=["a"],
            quality_checks={"x": True},
            evidence_commands=["c"],
            rollback_strategy="r",
            summary="s",
        )
        names = [r.name for r in gates.results]
        assert names == [
            GateName.SCOPE, GateName.QUALITY, GateName.EVIDENCE,
            GateName.RISK, GateName.COMMUNICATION,
        ]
