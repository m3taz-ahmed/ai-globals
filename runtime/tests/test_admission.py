"""Tests for runtime/admission.py — output admission gate + identity keys.

Implements Hazem Ali's representation/authority/memory principal: evaluate
the full chain from bytes → promoted context → runtime state → admitted
output. Side effects are blocked on reject (R1).
"""

from __future__ import annotations

from runtime.admission import (
    AdmissionGate,
    PromotionRecord,
    k_out,
    k_promote,
    k_repr,
    k_runtime,
)


class TestIdentityKeys:
    def test_k_repr_stable(self) -> None:
        k1 = k_repr("bytes1", "norm1", "tok1", "vocab1", "order1")
        k2 = k_repr("bytes1", "norm1", "tok1", "vocab1", "order1")
        assert k1 == k2
        assert k1.startswith("sha256:")

    def test_k_repr_changes_with_tokenizer(self) -> None:
        k1 = k_repr("bytes1", "norm1", "tok1", "vocab1", "order1")
        k2 = k_repr("bytes1", "norm1", "tok2", "vocab1", "order1")
        assert k1 != k2

    def test_k_promote_binds_lineage(self) -> None:
        repr_key = k_repr("b", "n", "t", "v", "o")
        k1 = k_promote(repr_key, ("blob://kb/v1",), "allow", "fresh", "not_deleted", "internal", "p1")
        k2 = k_promote(repr_key, ("blob://kb/v2",), "allow", "fresh", "not_deleted", "internal", "p1")
        assert k1 != k2

    def test_k_runtime_changes_with_precision(self) -> None:
        k1 = k_runtime("m", "w", "fp16", "b", "p", "d")
        k2 = k_runtime("m", "w", "fp32", "b", "p", "d")
        assert k1 != k2

    def test_k_out_binds_all(self) -> None:
        pk = k_promote(k_repr("b", "n", "t", "v", "o"), ("l",), "allow", "f", "nd", "i", "p")
        rk = k_runtime("m", "w", "fp16", "b", "p", "d")
        k1 = k_out(pk, rk, "eos", "out-pol-1")
        k2 = k_out(pk, rk, "length", "out-pol-1")
        assert k1 != k2


class TestPromotionRecord:
    def test_to_dict_serializes_lineage(self) -> None:
        rec = PromotionRecord(
            tenant_id="t1", subject_id="u1", candidate_id="doc1#chunk1",
            lineage=("blob://kb/v1",), retrieval_score=0.9, acl="allow",
            freshness="valid", deletion_state="not_deleted",
            classification="internal", policy_version="p1", decision="promote",
        )
        d = rec.to_dict()
        assert d["lineage"] == ["blob://kb/v1"]
        assert d["decision"] == "promote"


class TestAdmissionGate:
    def test_admit_on_clean_output(self) -> None:
        gate = AdmissionGate()
        ctx_hash = k_promote(k_repr("b", "n", "t", "v", "o"), ("l",), "allow", "f", "nd", "i", "p")
        rt_key = k_runtime("m", "w", "fp16", "b", "p", "d")
        rec = gate.admit(
            request_id="r1", context_hash=ctx_hash, runtime_key=rt_key,
            stop_reason="eos", schema_valid=True, evidence_coverage=0.9,
            policy_verdict="allow",
        )
        assert rec.admitted is True
        assert rec.decision == "admit"
        assert rec.reason_code == ""

    def test_reject_on_policy_deny(self) -> None:
        gate = AdmissionGate()
        rec = gate.admit(
            request_id="r1", context_hash="ch", runtime_key="rk",
            stop_reason="eos", schema_valid=True, evidence_coverage=0.9,
            policy_verdict="deny",
        )
        assert rec.decision == "reject"
        assert rec.reason_code == "policy_verdict_deny"
        # R1: side effects blocked — record not appended to admitted records
        assert rec not in gate.records

    def test_reject_on_invalid_schema(self) -> None:
        gate = AdmissionGate(require_schema_valid=True)
        rec = gate.admit(
            request_id="r1", context_hash="ch", runtime_key="rk",
            stop_reason="eos", schema_valid=False, evidence_coverage=0.9,
            policy_verdict="allow",
        )
        assert rec.decision == "reject"
        assert rec.reason_code == "schema_invalid"

    def test_reject_on_low_evidence_coverage(self) -> None:
        gate = AdmissionGate(min_evidence_coverage=0.8)
        rec = gate.admit(
            request_id="r1", context_hash="ch", runtime_key="rk",
            stop_reason="eos", schema_valid=True, evidence_coverage=0.5,
            policy_verdict="allow",
        )
        assert rec.decision == "reject"
        assert rec.reason_code == "evidence_coverage_below_threshold"

    def test_custom_check_rejects(self) -> None:
        gate = AdmissionGate()

        def no_pii(ctx: dict) -> tuple[bool, str]:
            if "ssn" in str(ctx).lower():
                return False, "pii_detected"
            return True, ""  # pragma: no cover

        gate.add_check("no_pii", no_pii)
        rec = gate.admit(
            request_id="r1", context_hash="ch", runtime_key="rk",
            stop_reason="eos", schema_valid=True, evidence_coverage=0.9,
            policy_verdict="allow", output_context={"ssn": "123-45-6789"},
        )
        assert rec.decision == "reject"
        assert "no_pii_failed" in rec.reason_code
        assert "pii_detected" in rec.reason_code

    def test_custom_check_exception_fail_closed(self) -> None:
        gate = AdmissionGate()

        def broken_check(ctx: dict) -> tuple[bool, str]:
            raise RuntimeError("check exploded")

        gate.add_check("broken", broken_check)
        rec = gate.admit(
            request_id="r1", context_hash="ch", runtime_key="rk",
            stop_reason="eos", schema_valid=True, evidence_coverage=0.9,
            policy_verdict="allow",
        )
        assert rec.decision == "reject"
        assert "check_broken_exception" in rec.reason_code

    def test_records_track_admitted_only(self) -> None:
        gate = AdmissionGate()
        gate.admit("r1", "ch", "rk", "eos", True, 0.9, "allow")
        gate.admit("r2", "ch", "rk", "eos", False, 0.9, "allow")
        assert len(gate.records) == 1
        assert gate.records[0].request_id == "r1"

    def test_reject_rate_metric(self) -> None:
        gate = AdmissionGate()
        gate.admit("r1", "ch", "rk", "eos", True, 0.9, "allow")
        gate.admit("r2", "ch", "rk", "eos", False, 0.9, "allow")
        # 1 admitted, 1 rejected → reject_rate = 0.5
        assert gate.reject_rate() == 0.5

    def test_reject_rate_by_reason(self) -> None:
        gate = AdmissionGate()
        gate.admit("r1", "ch", "rk", "eos", False, 0.9, "allow")
        gate.admit("r2", "ch", "rk", "eos", False, 0.9, "allow")
        rates = gate.reject_rate_by_reason()
        assert "schema_invalid" in rates
        assert rates["schema_invalid"] == 1.0

    def test_evaluate_promotion_blocks_deleted(self) -> None:
        gate = AdmissionGate()
        rec = PromotionRecord(
            tenant_id="t1", subject_id="u1", candidate_id="c1",
            lineage=("l",), retrieval_score=0.9, acl="allow",
            freshness="fresh", deletion_state="deleted",
            classification="internal", policy_version="p1", decision="promote",
        )
        assert gate.evaluate_promotion(rec) == "block"

    def test_evaluate_promotion_blocks_acl_deny(self) -> None:
        gate = AdmissionGate()
        rec = PromotionRecord(
            tenant_id="t1", subject_id="u1", candidate_id="c1",
            lineage=("l",), retrieval_score=0.9, acl="deny",
            freshness="fresh", deletion_state="not_deleted",
            classification="internal", policy_version="p1", decision="promote",
        )
        assert gate.evaluate_promotion(rec) == "block"

    def test_evaluate_promotion_allows_clean(self) -> None:
        gate = AdmissionGate()
        rec = PromotionRecord(
            tenant_id="t1", subject_id="u1", candidate_id="c1",
            lineage=("l",), retrieval_score=0.9, acl="allow",
            freshness="fresh", deletion_state="not_deleted",
            classification="internal", policy_version="p1", decision="promote",
        )
        assert gate.evaluate_promotion(rec) == "promote"

    def test_admission_record_output_key_binds_all(self) -> None:
        gate = AdmissionGate(admission_policy_version="out-pol-14")
        ctx_hash = k_promote(k_repr("b", "n", "t", "v", "o"), ("l",), "allow", "f", "nd", "i", "p")
        rt_key = k_runtime("m", "w", "fp16", "b", "p", "d")
        rec = gate.admit(
            request_id="r1", context_hash=ctx_hash, runtime_key=rt_key,
            stop_reason="eos", schema_valid=True, evidence_coverage=0.91,
            policy_verdict="allow",
        )
        expected_out = k_out(ctx_hash, rt_key, "eos", "out-pol-14")
        assert rec.output_key == expected_out
        assert rec.admission_policy == "out-pol-14"

    def test_admission_record_to_dict(self) -> None:
        gate = AdmissionGate()
        rec = gate.admit(
            request_id="r1", context_hash="ch", runtime_key="rk",
            stop_reason="eos", schema_valid=True, evidence_coverage=0.9,
            policy_verdict="allow",
        )
        d = rec.to_dict()
        assert d["request_id"] == "r1"
        assert d["decision"] == "admit"

    def test_all_records_includes_rejected(self) -> None:
        gate = AdmissionGate()
        gate.admit("r1", "ch", "rk", "eos", True, 0.9, "allow")
        gate.admit("r2", "ch", "rk", "eos", False, 0.9, "allow")
        assert len(gate.all_records) == 2

    def test_reject_rate_empty_returns_zero(self) -> None:
        gate = AdmissionGate()
        assert gate.reject_rate() == 0.0

    def test_reject_rate_by_reason_empty_returns_empty(self) -> None:
        gate = AdmissionGate()
        assert gate.reject_rate_by_reason() == {}

    def test_custom_check_pass_branch(self) -> None:
        gate = AdmissionGate()

        def no_pii(ctx: dict) -> tuple[bool, str]:
            if "ssn" in str(ctx).lower():
                return False, "pii_detected"  # pragma: no cover
            return True, ""

        gate.add_check("no_pii", no_pii)
        rec = gate.admit(
            request_id="r1", context_hash="ch", runtime_key="rk",
            stop_reason="eos", schema_valid=True, evidence_coverage=0.9,
            policy_verdict="allow", output_context={"safe": "data"},
        )
        assert rec.admitted is True
