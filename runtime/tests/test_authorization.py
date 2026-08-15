"""Tests for runtime/authorization.py — zero-trust PDP/PEP + receipt store.

Implements Hazem Ali's zero-trust AI execution principal: the model may
propose, but only an independent control plane may authorize consequence.
"""

from __future__ import annotations

from pathlib import Path

from runtime.authorization import (
    AuthorizationTuple,
    ExecutionReceipt,
    PermitDecision,
    PolicyDecisionPoint,
    PolicyEnforcementPoint,
    ReceiptStore,
    _scope_is_subset,
)


class TestScopeSubset:
    def test_empty_requested_allowed(self) -> None:
        assert _scope_is_subset((), ("read", "write")) is True

    def test_empty_delegated_denied(self) -> None:
        assert _scope_is_subset(("read",), ()) is False

    def test_subset_allowed(self) -> None:
        assert _scope_is_subset(("read",), ("read", "write")) is True

    def test_not_subset_denied(self) -> None:
        assert _scope_is_subset(("read", "admin",), ("read", "write")) is False


class TestAuthorizationTuple:
    def test_identity_hash_stable(self) -> None:
        tup = AuthorizationTuple(
            subject_id="u1", tenant_id="t1", workload_id="w1",
            operation_id="read", target_id="doc1",
        )
        assert tup.identity_hash() == tup.identity_hash()

    def test_identity_hash_changes_with_target(self) -> None:
        base = AuthorizationTuple(
            subject_id="u1", tenant_id="t1", workload_id="w1",
            operation_id="read", target_id="doc1",
        )
        other = AuthorizationTuple(
            subject_id="u1", tenant_id="t1", workload_id="w1",
            operation_id="read", target_id="doc2",
        )
        assert base.identity_hash() != other.identity_hash()

    def test_to_dict_serializes_scopes(self) -> None:
        tup = AuthorizationTuple(
            subject_id="u1", tenant_id="t1", workload_id="w1",
            operation_id="read", target_id="doc1",
            requested_scope=("read",), delegated_scope=("read", "write"),
        )
        d = tup.to_dict()
        assert d["requested_scope"] == ["read"]
        assert d["delegated_scope"] == ["read", "write"]


class TestPolicyDecisionPoint:
    def test_consequential_operation_asked(self) -> None:
        pdp = PolicyDecisionPoint()
        tup = AuthorizationTuple(
            subject_id="u1", tenant_id="t1", workload_id="w1",
            operation_id="deploy", target_id="prod",
            delegated_scope=("deploy",),
        )
        decision = pdp.decide(tup)
        assert decision.decision == "ask"
        assert "require_human_admission" in decision.obligations

    def test_non_consequential_allowed(self) -> None:
        pdp = PolicyDecisionPoint()
        tup = AuthorizationTuple(
            subject_id="u1", tenant_id="t1", workload_id="w1",
            operation_id="read", target_id="doc1",
            delegated_scope=("read",),
        )
        decision = pdp.decide(tup)
        assert decision.decision == "allow"
        assert decision.expires_at > 0

    def test_scope_violation_denied(self) -> None:
        pdp = PolicyDecisionPoint()
        tup = AuthorizationTuple(
            subject_id="u1", tenant_id="t1", workload_id="w1",
            operation_id="read", target_id="doc1",
            requested_scope=("admin",), delegated_scope=("read",),
        )
        decision = pdp.decide(tup)
        assert decision.decision == "deny"
        assert decision.reason == "requested_scope_not_subset_of_delegated"

    def test_fail_closed_on_pdp_outage_consequential(self) -> None:
        pdp = PolicyDecisionPoint(fail_closed=True)
        tup = AuthorizationTuple(
            subject_id="u1", tenant_id="t1", workload_id="w1",
            operation_id="deploy", target_id="prod",
            delegated_scope=("deploy",),
        )
        decision = pdp.decide(tup, pdp_available=False)
        assert decision.decision == "deny"
        assert decision.fail_closed is True
        assert decision.reason == ""

    def test_non_consequential_allowed_on_pdp_outage(self) -> None:
        pdp = PolicyDecisionPoint(fail_closed=True)
        tup = AuthorizationTuple(
            subject_id="u1", tenant_id="t1", workload_id="w1",
            operation_id="read", target_id="doc1",
            delegated_scope=("read",),
        )
        decision = pdp.decide(tup, pdp_available=False)
        assert decision.decision == "allow"

    def test_regulated_data_is_consequential(self) -> None:
        pdp = PolicyDecisionPoint()
        tup = AuthorizationTuple(
            subject_id="u1", tenant_id="t1", workload_id="w1",
            operation_id="read", target_id="doc1",
            data_classification="regulated",
            delegated_scope=("read",),
        )
        assert pdp.is_consequential(tup) is True

    def test_high_risk_denied(self) -> None:
        pdp = PolicyDecisionPoint(max_risk_score=0.8)
        tup = AuthorizationTuple(
            subject_id="u1", tenant_id="t1", workload_id="w1",
            operation_id="read", target_id="doc1",
            risk_score=0.9, delegated_scope=("read",),
        )
        decision = pdp.decide(tup)
        assert decision.decision == "deny"
        assert decision.reason == "risk_score_exceeds_threshold"

    def test_high_risk_marks_consequential(self) -> None:
        pdp = PolicyDecisionPoint(max_risk_score=0.8)
        tup = AuthorizationTuple(
            subject_id="u1", tenant_id="t1", workload_id="w1",
            operation_id="read", target_id="doc1",
            risk_score=0.85, delegated_scope=("read",),
        )
        assert pdp.is_consequential(tup) is True


class TestReceiptStore:
    def test_record_and_lookup(self, tmp_path: Path) -> None:
        store = ReceiptStore(tmp_path)
        rec = ExecutionReceipt(
            decision_id="dec-1", execution_id="exec-1",
            idempotency_key="idem-1", status="succeeded",
        )
        store.record(rec)
        assert store.lookup("idem-1") is not None
        assert store.lookup("idem-1").status == "succeeded"

    def test_idempotency_no_overwrite(self, tmp_path: Path) -> None:
        store = ReceiptStore(tmp_path)
        rec1 = ExecutionReceipt(
            decision_id="dec-1", execution_id="exec-1",
            idempotency_key="idem-1", status="succeeded",
        )
        rec2 = ExecutionReceipt(
            decision_id="dec-1", execution_id="exec-2",
            idempotency_key="idem-1", status="failed",
        )
        store.record(rec1)
        store.record(rec2)  # must not overwrite
        assert store.lookup("idem-1").status == "succeeded"

    def test_lookup_missing_returns_none(self, tmp_path: Path) -> None:
        store = ReceiptStore(tmp_path)
        assert store.lookup("nonexistent") is None

    def test_persistence_across_instances(self, tmp_path: Path) -> None:
        store1 = ReceiptStore(tmp_path)
        rec = ExecutionReceipt(
            decision_id="dec-1", execution_id="exec-1",
            idempotency_key="idem-1", status="succeeded",
        )
        store1.record(rec)
        store2 = ReceiptStore(tmp_path)
        assert store2.lookup("idem-1") is not None

    def test_load_skips_blank_and_invalid_lines(self, tmp_path: Path) -> None:
        store_file = tmp_path / "state" / "receipts.jsonl"
        store_file.parent.mkdir(parents=True, exist_ok=True)
        store_file.write_text(
            '\n'
            'not valid json\n'
            '{"decision_id": "dec-1"}\n'
            '\n'
            '{"decision_id": "dec-1", "execution_id": "exec-1", "idempotency_key": "idem-1", "status": "succeeded"}\n',
            encoding="utf-8",
        )
        store = ReceiptStore(tmp_path)
        assert store.lookup("idem-1") is not None
        assert store.lookup("idem-1").status == "succeeded"


class TestPolicyEnforcementPoint:
    def test_schema_drift_rejected(self, tmp_path: Path) -> None:
        store = ReceiptStore(tmp_path)
        pep = PolicyEnforcementPoint(store)
        tup = AuthorizationTuple(
            subject_id="u1", tenant_id="t1", workload_id="w1",
            operation_id="write", target_id="doc1",
            arguments_schema_hash="sha256:abc",
            delegated_scope=("write",),
        )
        decision = PermitDecision(
            decision="allow", decision_id="dec-1", tuple_hash=tup.identity_hash(),
        )
        result = pep.enforce(tup, decision, observed_schema_hash="sha256:xyz")
        assert isinstance(result, PermitDecision)
        assert result.decision == "deny"
        assert result.reason == "schema_hash_mismatch_tool_drift"

    def test_target_swap_rejected(self, tmp_path: Path) -> None:
        store = ReceiptStore(tmp_path)
        pep = PolicyEnforcementPoint(store)
        tup = AuthorizationTuple(
            subject_id="u1", tenant_id="t1", workload_id="w1",
            operation_id="write", target_id="doc1",
            delegated_scope=("write",),
        )
        decision = PermitDecision(
            decision="allow", decision_id="dec-1", tuple_hash=tup.identity_hash(),
        )
        result = pep.enforce(tup, decision, observed_target_id="doc2")
        assert isinstance(result, PermitDecision)
        assert result.decision == "deny"
        assert result.reason == "target_binding_mismatch"

    def test_idempotency_reconciliation(self, tmp_path: Path) -> None:
        store = ReceiptStore(tmp_path)
        pep = PolicyEnforcementPoint(store)
        rec = ExecutionReceipt(
            decision_id="dec-1", execution_id="exec-1",
            idempotency_key="idem-1", status="succeeded",
        )
        store.record(rec)
        tup = AuthorizationTuple(
            subject_id="u1", tenant_id="t1", workload_id="w1",
            operation_id="write", target_id="doc1",
            idempotency_key="idem-1", delegated_scope=("write",),
        )
        decision = PermitDecision(
            decision="allow", decision_id="dec-1", tuple_hash=tup.identity_hash(),
        )
        result = pep.enforce(tup, decision)
        assert isinstance(result, ExecutionReceipt)
        assert result.status == "succeeded"

    def test_reconcile_timeout_returns_receipt(self, tmp_path: Path) -> None:
        store = ReceiptStore(tmp_path)
        pep = PolicyEnforcementPoint(store)
        rec = ExecutionReceipt(
            decision_id="dec-1", execution_id="exec-1",
            idempotency_key="idem-1", status="succeeded",
        )
        store.record(rec)
        tup = AuthorizationTuple(
            subject_id="u1", tenant_id="t1", workload_id="w1",
            operation_id="write", target_id="doc1",
            idempotency_key="idem-1", delegated_scope=("write",),
        )
        result = pep.reconcile_timeout(tup)
        assert result is not None
        assert result.status == "succeeded"

    def test_reconcile_timeout_no_key_returns_none(self, tmp_path: Path) -> None:
        store = ReceiptStore(tmp_path)
        pep = PolicyEnforcementPoint(store)
        tup = AuthorizationTuple(
            subject_id="u1", tenant_id="t1", workload_id="w1",
            operation_id="write", target_id="doc1",
            delegated_scope=("write",),
        )
        assert pep.reconcile_timeout(tup) is None

    def test_allow_passes_through(self, tmp_path: Path) -> None:
        store = ReceiptStore(tmp_path)
        pep = PolicyEnforcementPoint(store)
        tup = AuthorizationTuple(
            subject_id="u1", tenant_id="t1", workload_id="w1",
            operation_id="write", target_id="doc1",
            delegated_scope=("write",),
        )
        decision = PermitDecision(
            decision="allow", decision_id="dec-1", tuple_hash=tup.identity_hash(),
        )
        result = pep.enforce(tup, decision, observed_target_id="doc1")
        assert result is decision

    def test_deny_decision_returned_unchanged(self, tmp_path: Path) -> None:
        store = ReceiptStore(tmp_path)
        pep = PolicyEnforcementPoint(store)
        tup = AuthorizationTuple(
            subject_id="u1", tenant_id="t1", workload_id="w1",
            operation_id="write", target_id="doc1",
            delegated_scope=("write",),
        )
        decision = PermitDecision(
            decision="deny", decision_id="dec-1", tuple_hash=tup.identity_hash(),
            reason="risk_score_exceeds_threshold",
        )
        result = pep.enforce(tup, decision, observed_target_id="doc1")
        assert result is decision
