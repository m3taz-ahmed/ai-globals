#!/usr/bin/env python3
"""Output admission gate for aiZee.

Implements Hazem Ali's representation/authority/memory principal: do not
evaluate AI correctness from output text alone. Evaluate the full chain
from bytes → promoted context → runtime state → admitted output.

The admission gate runs BEFORE any side effect. Termination does not imply
correctness, safety, or completeness — admission is the final
consequence-aware check that decides whether generated output can be used
downstream.

This module provides:
- Identity keys: ``K_repr``, ``K_promote``, ``K_runtime``, ``K_out`` —
  implementation-agnostic formulas that force evidence discipline by
  separating representation, promotion, runtime, and outcome identities.
- ``PromotionRecord``: evidence of a retrieval candidate's promotion decision.
- ``AdmissionRecord``: evidence of the final output admission verdict.
- ``AdmissionGate``: the gate that enforces consequence-tier checks before
  publication. Side effects are blocked on reject (R1 invariant).

Reference: principals/ai-systems/01-representation-authority-and-memory.md
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

_logger = logging.getLogger(__name__)

# Invariants (Hazem R1-R15, adapted — see rules/architecture-review.md):
#   R1: no high-consequence action without an admitted output record.
#   R2: every admitted output links to one final context hash.
#   R3: every final context hash links to one promotion decision set.
#   R4: promotion decisions include tenant, subject, policy version, lineage.
#   R5: serving-state reuse only when compatibility key matches exactly.
#   R6: cache namespace always includes tenant boundary fields.
#   R7: trace spans never store secrets in attributes.
#   R8: if admission fails, response carries machine-readable reason code.
#   R9: if deletion status changes, future promotions from affected lineage blocked.
#   R10: if tokenizer artifact changes, cached representation identity invalidated.

AdmissionVerdict = Literal["admit", "reject", "quarantine"]


def _sha256(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def k_repr(
    byte_digest: str,
    normalization_version: str,
    tokenizer_artifact: str,
    vocab_checksum: str,
    envelope_ordering: str,
    multimodal_identity: str = "",
) -> str:
    """Representation identity key: K_repr = H(B, N, T, V, O, M).

    Separates byte identity from normalization/tokenizer/envelope identity
    so that the same rendered text mapping to different token IDs across
    tokenizer revisions is detectable.
    """
    return _sha256({
        "B": byte_digest,
        "N": normalization_version,
        "T": tokenizer_artifact,
        "V": vocab_checksum,
        "O": envelope_ordering,
        "M": multimodal_identity,
    })


def k_promote(
    repr_key: str,
    lineage: tuple[str, ...],
    acl_decision: str,
    freshness: str,
    deletion_state: str,
    classification: str,
    policy_version: str,
) -> str:
    """Promotion identity key: K_promote = H(K_repr, L, A, F, D, C, P).

    Binds a promoted context chunk to its authority evidence (ACL, freshness,
    deletion state, classification, policy version). Retrieval rank alone
    does not encode permission or current legal-hold state.
    """
    return _sha256({
        "K_repr": repr_key,
        "L": list(lineage),
        "A": acl_decision,
        "F": freshness,
        "D": deletion_state,
        "C": classification,
        "P": policy_version,
    })


def k_runtime(
    model: str,
    weights: str,
    precision: str,
    backend: str,
    positioning: str,
    decode_policy: str,
) -> str:
    """Runtime compatibility key: K_runtime = H(Model, Weights, Precision,
    Backend, Positioning, DecodePolicy).

    Serving-state reuse is allowed only when this key matches exactly (R5).
    A change in precision mode or decode policy invalidates deterministic
    tier labels (R11, R12).
    """
    return _sha256({
        "Model": model,
        "Weights": weights,
        "Precision": precision,
        "Backend": backend,
        "Positioning": positioning,
        "DecodePolicy": decode_policy,
    })


def k_out(
    promote_key: str,
    runtime_key: str,
    stop_reason: str,
    admission_policy_version: str,
) -> str:
    """Admitted output identity: K_out = H(K_promote, K_runtime, StopReason,
    AdmissionPolicyVersion).

    The only compact identifier of actual model-visible evidence + the
    runtime that produced it + the policy that admitted it.
    """
    return _sha256({
        "K_promote": promote_key,
        "K_runtime": runtime_key,
        "StopReason": stop_reason,
        "AdmissionPolicyVersion": admission_policy_version,
    })


@dataclass
class PromotionRecord:
    """Evidence of a single retrieval candidate's promotion decision.

    Retrieval is recall optimization, not authority proof. The promotion
    gate evaluates authority and policy constraints (ACL, freshness,
    deletion, classification) before a candidate enters model context.
    """

    tenant_id: str
    subject_id: str
    candidate_id: str
    lineage: tuple[str, ...]
    retrieval_score: float
    acl: str  # "allow" | "deny"
    freshness: str
    deletion_state: str  # "not_deleted" | "deleted"
    classification: str
    policy_version: str
    decision: str  # "promote" | "block"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["lineage"] = list(self.lineage)
        return d


@dataclass
class AdmissionRecord:
    """Evidence of the final output admission verdict.

    R1: no high-consequence action is allowed without an admitted output
    record. R8: if admission fails, the response carries a machine-readable
    reason code.
    """

    request_id: str
    context_hash: str  # K_promote of the final promoted context
    runtime_key: str  # K_runtime
    output_key: str  # K_out
    stop_reason: str
    schema_valid: bool
    evidence_coverage: float
    policy_verdict: str  # "allow" | "deny"
    admission_policy: str
    decision: AdmissionVerdict
    reason_code: str = ""
    admitted_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def admitted(self) -> bool:
        return self.decision == "admit"


# A check function returns (passed: bool, reason_code: str).
CheckFn = Callable[[dict[str, Any]], tuple[bool, str]]


class AdmissionGate:
    """Output admission gate — enforces consequence-tier checks before any
    side effect.

    The gate is independent from model generation (data plane). It runs
    AFTER the model produces output but BEFORE the output is published or
    used to trigger side effects. Termination (stop_reason) does not imply
    correctness — admission is the final consequence-aware check.

    Side effects are blocked on reject (R1). A rejected request must
    explain itself to an operator with a machine-readable reason code (R8).
    """

    def __init__(
        self,
        admission_policy_version: str = "out-pol-1",
        *,
        min_evidence_coverage: float = 0.0,
        require_schema_valid: bool = True,
    ) -> None:
        self.admission_policy_version = admission_policy_version
        self.min_evidence_coverage = min_evidence_coverage
        self.require_schema_valid = require_schema_valid
        self._checks: list[tuple[str, CheckFn]] = []
        self._records: list[AdmissionRecord] = []

    def add_check(self, name: str, fn: CheckFn) -> None:
        """Register a custom admission check.

        A check receives the output context dict and returns
        (passed, reason_code). The first failing check rejects the output.
        """
        self._checks.append((name, fn))

    def evaluate_promotion(self, candidate: PromotionRecord) -> str:
        """Evaluate whether a retrieval candidate may be promoted into
        model context.

        R9: if deletion status changes, future promotions from affected
        lineage are blocked. ACL must be allow; deletion must be not_deleted.
        """
        if candidate.deletion_state == "deleted":
            return "block"
        if candidate.acl != "allow":
            return "block"
        return candidate.decision

    def admit(
        self,
        request_id: str,
        context_hash: str,
        runtime_key: str,
        stop_reason: str,
        schema_valid: bool,
        evidence_coverage: float,
        policy_verdict: str,
        output_context: dict[str, Any] | None = None,
    ) -> AdmissionRecord:
        """Run the admission gate and return an AdmissionRecord.

        R1: side effects must be blocked when decision != "admit".
        R8: a reject carries a machine-readable reason_code.
        """
        out_key = k_out(
            context_hash, runtime_key, stop_reason, self.admission_policy_version
        )
        ctx = output_context or {}
        common = (request_id, context_hash, runtime_key, out_key, stop_reason,
                  schema_valid, evidence_coverage, policy_verdict)
        reject = self._evaluate_gates(ctx, schema_valid, evidence_coverage, policy_verdict)
        if reject is not None:
            return self._build_record(*common, "reject", reject)
        return self._build_record(*common, "admit", "")

    def _evaluate_gates(
        self, ctx: dict[str, Any], schema_valid: bool,
        evidence_coverage: float, policy_verdict: str,
    ) -> str | None:
        """Run all admission gates. Returns reason_code if rejected, None if ok."""
        if policy_verdict == "deny":
            return "policy_verdict_deny"
        if self.require_schema_valid and not schema_valid:
            return "schema_invalid"
        if evidence_coverage < self.min_evidence_coverage:
            return "evidence_coverage_below_threshold"
        return self._run_custom_checks(ctx)

    def _run_custom_checks(self, ctx: dict[str, Any]) -> str | None:
        """Run custom checks — first failure rejects."""
        for name, fn in self._checks:
            try:
                passed, reason = fn(ctx)
            except Exception as exc:
                _logger.debug("admission check %s failed: %s", name, exc, exc_info=True)
                passed, reason = False, f"check_{name}_exception:{exc}"
            if not passed:
                return f"check_{name}_failed:{reason}"
        return None

    def _build_record(
        self,
        request_id: str,
        context_hash: str,
        runtime_key: str,
        out_key: str,
        stop_reason: str,
        schema_valid: bool,
        evidence_coverage: float,
        policy_verdict: str,
        decision: AdmissionVerdict,
        reason_code: str,
    ) -> AdmissionRecord:
        record = AdmissionRecord(
            request_id=request_id,
            context_hash=context_hash,
            runtime_key=runtime_key,
            output_key=out_key,
            stop_reason=stop_reason,
            schema_valid=schema_valid,
            evidence_coverage=evidence_coverage,
            policy_verdict=policy_verdict,
            admission_policy=self.admission_policy_version,
            decision=decision,
            reason_code=reason_code,
        )
        # Track ALL decisions (admitted + rejected) for metrics.
        self._records.append(record)
        return record

    @property
    def records(self) -> list[AdmissionRecord]:
        """Admitted records only (R1: side effects blocked on reject)."""
        return [r for r in self._records if r.admitted]

    @property
    def all_records(self) -> list[AdmissionRecord]:
        """All admission decisions (admitted + rejected) for metrics."""
        return list(self._records)

    def reject_rate(self) -> float:
        """Metric: admission_reject_rate. Useful for SLO monitoring."""
        if not self._records:
            return 0.0
        rejected = sum(1 for r in self._records if r.decision != "admit")
        return rejected / len(self._records)

    def reject_rate_by_reason(self) -> dict[str, float]:
        """Metric: admission_reject_rate by reason_code."""
        if not self._records:
            return {}
        counts: dict[str, int] = {}
        for r in self._records:
            if r.decision != "admit" and r.reason_code:
                counts[r.reason_code] = counts.get(r.reason_code, 0) + 1
        total = len(self._records)
        return {k: v / total for k, v in counts.items()}
