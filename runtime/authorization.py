#!/usr/bin/env python3
"""Capability-scoped authorization for AI Global OS.

Implements Hazem Ali's zero-trust AI execution principal: the model may propose,
but only an independent control plane may authorize consequence.

This module is cloud-agnostic. It provides:
- ``AuthorizationTuple``: the full context bound to a single permit decision.
- ``Permit``: a deterministic decision function ``f(subject, workload, tenant,
  task, operation, target, data_class, env, risk, time)``.
- ``ReceiptStore``: append-only store of execution receipts keyed by
  idempotency key, so ambiguous timeouts can be reconciled without retry storms.
- ``PolicyDecisionPoint``: independent decision component (PDP) separate from
  the model/executor (data plane).
- ``PolicyEnforcementPoint``: validates schema hash, target binding, and limits
  before launching reduced-authority execution (PEP).

Reference: principals/cybersecurity/01-zero-trust-ai-execution.md
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

# A permit decision is never inferred from model confidence.
Decision = Literal["allow", "deny", "ask"]

# Hard invariants (Hazem, cybersecurity/01):
#   - admitted scope is a subset of delegated scope.
#   - control-plane outage fails closed for consequential operations.
#   - each write has one idempotency key and one receipt id.
#   - a policy decision cannot be reused across different targets.
#   - tool output is untrusted until revalidated at the next boundary.


@dataclass(frozen=True)
class AuthorizationTuple:
    """The full context bound to a single permit decision.

    Authorize a specific operation, not a broad capability class.
    ``Permit = f(subject, workload, tenant, task, operation, target,
                 data_class, env, risk, time)``.
    """

    subject_id: str
    tenant_id: str
    workload_id: str
    operation_id: str
    target_id: str
    requested_scope: tuple[str, ...] = ()
    data_classification: str = "internal"
    idempotency_key: str = ""
    execution_deadline_s: float = 0.0
    risk_score: float = 0.0
    environment: str = "dev"
    arguments_schema_hash: str = ""
    delegated_scope: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["requested_scope"] = list(self.requested_scope)
        d["delegated_scope"] = list(self.delegated_scope)
        return d

    def identity_hash(self) -> str:
        """Stable hash of the tuple for audit linkage (excludes deadline/risk)."""
        payload = {
            "subject_id": self.subject_id,
            "tenant_id": self.tenant_id,
            "workload_id": self.workload_id,
            "operation_id": self.operation_id,
            "target_id": self.target_id,
            "data_classification": self.data_classification,
            "environment": self.environment,
            "arguments_schema_hash": self.arguments_schema_hash,
        }
        canonical = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass
class PermitDecision:
    """Result of a PDP evaluation."""

    decision: Decision
    decision_id: str
    tuple_hash: str
    obligations: list[str] = field(default_factory=list)
    expires_at: float = 0.0
    reason: str = ""

    @property
    def allowed(self) -> bool:
        return self.decision == "allow"

    @property
    def fail_closed(self) -> bool:
        """A deny with empty reason indicates fail-closed (e.g. PDP outage)."""
        return self.decision == "deny" and not self.reason


def _scope_is_subset(requested: tuple[str, ...], delegated: tuple[str, ...]) -> bool:
    """Invariant: admitted scope is a subset of delegated scope."""
    if not requested:
        return True
    if not delegated:
        return False
    return set(requested).issubset(set(delegated))


class PolicyDecisionPoint:
    """Independent decision component (PDP).

    Separated from the model/executor (data plane). Only the PDP may
    authorize consequence. A control-plane outage fails closed for
    consequential operations.
    """

    def __init__(
        self,
        *,
        fail_closed: bool = True,
        consequential_operations: tuple[str, ...] = (
            "deploy", "release", "delete", "drop", "truncate", "destroy",
            "git.commit", "git.push", "spend", "grant_access",
        ),
        max_risk_score: float = 0.8,
    ) -> None:
        self.fail_closed = fail_closed
        self.consequential_operations = set(consequential_operations)
        self.max_risk_score = max_risk_score

    def is_consequential(self, tup: AuthorizationTuple) -> bool:
        """An operation is consequential if it can affect money, access,
        safety, production, or regulated data, OR if it is in the
        consequential set, OR if data classification is regulated."""
        if tup.operation_id in self.consequential_operations:
            return True
        if tup.data_classification in ("regulated", "secret", "top_secret"):
            return True
        return tup.risk_score >= self.max_risk_score

    def decide(self, tup: AuthorizationTuple, *, pdp_available: bool = True) -> PermitDecision:
        """Evaluate the tuple and return a permit decision.

        Hard invariants enforced:
        - admitted scope is a subset of delegated scope (else deny).
        - a policy decision cannot be reused across different targets
          (each tuple carries its own target_id; the hash binds it).
        - consequential operations fail closed when PDP is unavailable.
        - risk above threshold denies.
        """
        import uuid as _uuid

        decision_id = f"dec-{_uuid.uuid4().hex[:12]}"
        tuple_hash = tup.identity_hash()

        # Fail-closed for consequential ops when PDP is unavailable.
        if not pdp_available and self.fail_closed and self.is_consequential(tup):
            return PermitDecision(
                decision="deny",
                decision_id=decision_id,
                tuple_hash=tuple_hash,
                reason="",
            )

        # Scope invariant: requested must be subset of delegated.
        if not _scope_is_subset(tup.requested_scope, tup.delegated_scope):
            return PermitDecision(
                decision="deny",
                decision_id=decision_id,
                tuple_hash=tuple_hash,
                reason="requested_scope_not_subset_of_delegated",
            )

        # Risk gate — hard deny before consequential classification.
        if tup.risk_score >= self.max_risk_score:
            return PermitDecision(
                decision="deny",
                decision_id=decision_id,
                tuple_hash=tuple_hash,
                reason="risk_score_exceeds_threshold",
            )

        # Consequential operations require human admission (ask) unless
        # an explicit allow rule is wired by the caller.
        if self.is_consequential(tup):
            return PermitDecision(
                decision="ask",
                decision_id=decision_id,
                tuple_hash=tuple_hash,
                obligations=[
                    "require_human_admission",
                    "require_receipt",
                    "require_immutable_audit",
                ],
                reason="consequential_requires_admission",
            )

        # Default: allow non-consequential, in-scope, low-risk operations.
        expires = time.time() + max(tup.execution_deadline_s, 60.0)
        return PermitDecision(
            decision="allow",
            decision_id=decision_id,
            tuple_hash=tuple_hash,
            obligations=["require_receipt"] if tup.idempotency_key else [],
            expires_at=expires,
        )


@dataclass
class ExecutionReceipt:
    """Immutable evidence of an admitted execution outcome."""

    decision_id: str
    execution_id: str
    idempotency_key: str
    status: str  # "succeeded" | "failed" | "ambiguous"
    side_effect_receipt: str = ""
    result_ref: str = ""
    observed_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ReceiptStore:
    """Append-only store of execution receipts keyed by idempotency key.

    Enables ambiguous-outcome reconciliation: on timeout after dispatch,
    query the receipt store by idempotency key before retrying. If a
    receipt exists, return the stored outcome instead of re-executing.
    """

    def __init__(self, root: Path) -> None:
        self.root = root
        self.store_file = root / "state" / "receipts.jsonl"
        self.store_file.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._index: dict[str, ExecutionReceipt] = {}
        self._load()

    def _load(self) -> None:
        if not self.store_file.exists():
            return
        with self.store_file.open("r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    obj = json.loads(stripped)
                    rec = ExecutionReceipt(
                        decision_id=obj["decision_id"],
                        execution_id=obj["execution_id"],
                        idempotency_key=obj["idempotency_key"],
                        status=obj["status"],
                        side_effect_receipt=obj.get("side_effect_receipt", ""),
                        result_ref=obj.get("result_ref", ""),
                        observed_at=obj.get("observed_at", 0.0),
                    )
                    self._index[rec.idempotency_key] = rec
                except (json.JSONDecodeError, KeyError):
                    continue

    def record(self, receipt: ExecutionReceipt) -> None:
        """Append a receipt. One idempotency key → one receipt."""
        with self._lock:
            if receipt.idempotency_key and receipt.idempotency_key in self._index:
                # Idempotency invariant: do not overwrite an existing receipt.
                return
            with self.store_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(receipt.to_dict(), default=str) + "\n")
            self._index[receipt.idempotency_key] = receipt

    def lookup(self, idempotency_key: str) -> ExecutionReceipt | None:
        """Query the receipt store by idempotency key.

        Use this before retrying an ambiguous write. If a receipt exists,
        return the stored outcome; do not re-execute.
        """
        return self._index.get(idempotency_key)


class PolicyEnforcementPoint:
    """Validates schema hash, target binding, and limits before launching
    reduced-authority execution (PEP).

    The PEP is the enforcement component; it does NOT make policy decisions
    (that is the PDP's job). It validates that the admitted decision still
    matches the operation about to execute.
    """

    def __init__(self, receipt_store: ReceiptStore) -> None:
        self.receipt_store = receipt_store

    def enforce(
        self,
        tup: AuthorizationTuple,
        decision: PermitDecision,
        *,
        observed_schema_hash: str = "",
        observed_target_id: str = "",
    ) -> PermitDecision | ExecutionReceipt:
        """Validate the decision against observed runtime values.

        Returns:
        - The original ``PermitDecision`` if enforcement passes.
        - A denied ``PermitDecision`` if schema hash or target binding
          mismatches (tool schema drift / target swap attack).
        - An existing ``ExecutionReceipt`` if the idempotency key already
          has a receipt (ambiguous-outcome reconciliation).
        """
        # Idempotency reconciliation: if we already have a receipt, return it.
        if tup.idempotency_key:
            existing = self.receipt_store.lookup(tup.idempotency_key)
            if existing is not None:
                return existing

        # Schema hash binding: reject if the tool schema drifted.
        if (
            tup.arguments_schema_hash
            and observed_schema_hash
            and observed_schema_hash != tup.arguments_schema_hash
        ):
            import uuid as _uuid
            return PermitDecision(
                decision="deny",
                decision_id=f"dec-{_uuid.uuid4().hex[:12]}",
                tuple_hash=tup.identity_hash(),
                reason="schema_hash_mismatch_tool_drift",
            )

        # Target binding: reject if the resolved target differs from the
        # admitted target (target swap attack).
        if observed_target_id and observed_target_id != tup.target_id:
            import uuid as _uuid
            return PermitDecision(
                decision="deny",
                decision_id=f"dec-{_uuid.uuid4().hex[:12]}",
                tuple_hash=tup.identity_hash(),
                reason="target_binding_mismatch",
            )

        # Decision must be an allow to proceed.
        if not decision.allowed:
            return decision

        return decision

    def reconcile_timeout(self, tup: AuthorizationTuple) -> ExecutionReceipt | None:
        """Ambiguous-outcome rule: on timeout after dispatch, query the
        receipt store by idempotency key before retrying."""
        if not tup.idempotency_key:
            return None
        return self.receipt_store.lookup(tup.idempotency_key)
