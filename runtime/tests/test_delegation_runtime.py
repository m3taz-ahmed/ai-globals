"""Tests for authorization enhancements — Delegation, Provenance, Runtime State."""

from __future__ import annotations

from runtime.authorization import (
    AuthorizationTuple,
    DelegationMode,
    PolicyDecisionPoint,
    Provenance,
    RuntimeOrchestrator,
    RuntimeState,
)


class TestDelegationMode:
    def test_default_delegation_is_inherit(self) -> None:
        tup = AuthorizationTuple(
            subject_id="u1", tenant_id="t1", workload_id="w1",
            operation_id="read", target_id="doc1",
        )
        assert tup.delegation_mode == DelegationMode.INHERIT

    def test_delegation_mode_none(self) -> None:
        tup = AuthorizationTuple(
            subject_id="u1", tenant_id="t1", workload_id="w1",
            operation_id="read", target_id="doc1",
            delegation_mode=DelegationMode.NONE,
        )
        assert tup.delegation_mode == DelegationMode.NONE

    def test_hop_count_default_zero(self) -> None:
        tup = AuthorizationTuple(
            subject_id="u1", tenant_id="t1", workload_id="w1",
            operation_id="read", target_id="doc1",
        )
        assert tup.hop_count == 0


class TestProvenance:
    def test_default_provenance_is_user_trusted(self) -> None:
        tup = AuthorizationTuple(
            subject_id="u1", tenant_id="t1", workload_id="w1",
            operation_id="read", target_id="doc1",
        )
        assert tup.provenance == Provenance.USER_TRUSTED

    def test_external_untrusted_denies_consequential(self) -> None:
        pdp = PolicyDecisionPoint()
        tup = AuthorizationTuple(
            subject_id="u1", tenant_id="t1", workload_id="w1",
            operation_id="deploy", target_id="prod",
            delegated_scope=("deploy",),
            provenance=Provenance.EXTERNAL_UNTRUSTED,
        )
        decision = pdp.decide(tup)
        assert decision.decision == "deny"
        assert "external_untrusted" in decision.reason

    def test_user_trusted_can_ask_for_consequential(self) -> None:
        pdp = PolicyDecisionPoint()
        tup = AuthorizationTuple(
            subject_id="u1", tenant_id="t1", workload_id="w1",
            operation_id="deploy", target_id="prod",
            delegated_scope=("deploy",),
            provenance=Provenance.USER_TRUSTED,
        )
        decision = pdp.decide(tup)
        assert decision.decision == "ask"


class TestRuntimeOrchestrator:
    def test_legal_transition_idle_to_intent(self) -> None:
        orch = RuntimeOrchestrator()
        assert orch.state == RuntimeState.IDLE
        orch.transition(RuntimeState.INTENT_SET)
        assert orch.state == RuntimeState.INTENT_SET

    def test_legal_full_cycle(self) -> None:
        orch = RuntimeOrchestrator()
        orch.transition(RuntimeState.INTENT_SET)
        orch.transition(RuntimeState.PLAN_APPROVED)
        orch.transition(RuntimeState.EXECUTING)
        orch.transition(RuntimeState.TERMINATED)
        assert orch.state == RuntimeState.TERMINATED

    def test_illegal_transition_raises(self) -> None:
        orch = RuntimeOrchestrator()
        import pytest
        with pytest.raises(ValueError, match="Illegal state transition"):
            orch.transition(RuntimeState.EXECUTING)

    def test_can_issue_authority_only_in_executing(self) -> None:
        orch = RuntimeOrchestrator()
        assert orch.can_issue_authority() is False
        orch.transition(RuntimeState.INTENT_SET)
        assert orch.can_issue_authority() is False
        orch.transition(RuntimeState.PLAN_APPROVED)
        assert orch.can_issue_authority() is False
        orch.transition(RuntimeState.EXECUTING)
        assert orch.can_issue_authority() is True

    def test_reset_to_idle(self) -> None:
        orch = RuntimeOrchestrator()
        orch.transition(RuntimeState.INTENT_SET)
        orch.reset()
        assert orch.state == RuntimeState.IDLE

    def test_terminated_is_terminal(self) -> None:
        orch = RuntimeOrchestrator()
        orch.transition(RuntimeState.INTENT_SET)
        orch.transition(RuntimeState.TERMINATED)
        import pytest
        with pytest.raises(ValueError):
            orch.transition(RuntimeState.IDLE)
