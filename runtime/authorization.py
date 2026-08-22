#!/usr/bin/env python3
"""Capability-scoped authorization for aiZee.

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

import fnmatch
import hashlib
import json
import re
import threading
import time
import uuid as _uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Literal

# A permit decision is never inferred from model confidence.
Decision = Literal["allow", "deny", "ask"]


class EnforcementMode(str, Enum):
    """Three enforcement modes for the PEP (from agent-policy-engine)."""

    DISABLED = "disabled"  # Development only — tools execute directly
    OBSERVE = "observe"    # Log policy evaluation but proceed
    ENFORCE = "enforce"    # Full enforcement — block without authority


class DelegationMode(str, Enum):
    """Three-mode delegation (from caracal).

    - inherit: carries parent's effective authority forward
    - narrow: issues bounded delegation (server re-validates subset)
    - none: starts child explicitly delegation-less
    """

    INHERIT = "inherit"
    NARROW = "narrow"
    NONE = "none"


class Provenance(str, Enum):
    """Data provenance labels (from agent-policy-engine).

    External data cannot create authority — only USER_TRUSTED inputs
    can grant authority for consequential operations.
    """

    USER_TRUSTED = "user_trusted"
    EXTERNAL_UNTRUSTED = "external_untrusted"
    SYSTEM_GENERATED = "system_generated"


class RuntimeState(str, Enum):
    """Runtime state machine (from agent-policy-engine).

    Illegal transitions are rejected. Authority issuance only
    allowed in EXECUTING state.
    """

    IDLE = "idle"
    INTENT_SET = "intent_set"
    PLAN_APPROVED = "plan_approved"
    EXECUTING = "executing"
    TERMINATED = "terminated"


# Legal state transitions (from agent-policy-engine)
_LEGAL_TRANSITIONS: dict[RuntimeState, set[RuntimeState]] = {
    RuntimeState.IDLE: {RuntimeState.INTENT_SET},
    RuntimeState.INTENT_SET: {RuntimeState.PLAN_APPROVED, RuntimeState.TERMINATED},
    RuntimeState.PLAN_APPROVED: {RuntimeState.EXECUTING, RuntimeState.TERMINATED},
    RuntimeState.EXECUTING: {RuntimeState.TERMINATED},
    RuntimeState.TERMINATED: set(),
}


@dataclass
class DelegationConstraints:
    """Typed delegation limits (from caracal).

    Prevents infinite delegation chains via max_hops and max_depth.
    """

    resources: list[str] | None = None
    max_depth: int | None = None
    max_hops: int | None = None
    ttl_seconds: int | None = None
    policy_approved: bool = False
    broad_reason: str = ""

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
    lease_generation: int = 0  # Fencing token to prevent stale session recovery
    delegation_mode: DelegationMode = DelegationMode.INHERIT
    hop_count: int = 0  # Delegation chain depth
    provenance: Provenance = Provenance.USER_TRUSTED

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


class ConditionEvaluator:
    """Evaluates parameterized conditions on action parameters (DAE Standard).

    Supports constraint types: prefix, suffix, allowlist, denylist,
    max, min, regex, equals. Used by the PDP for fine-grained policy
    enforcement without code changes.
    """

    @staticmethod
    def evaluate(
        parameters: dict[str, Any],
        conditions: dict[str, Any],
    ) -> list[str]:
        """Return list of failure messages (empty = all conditions pass)."""
        failures: list[str] = []
        for param_name, constraints in conditions.items():
            param_value = parameters.get(param_name)
            for ctype, cvalue in constraints.items():
                msg = ConditionEvaluator._check(
                    param_name, param_value, ctype, cvalue,
                )
                if msg:
                    failures.append(msg)
        return failures

    @staticmethod
    def _check(
        name: str, value: Any, ctype: str, cvalue: Any,
    ) -> str | None:
        """Check a single constraint. Returns failure message or None."""
        if ctype == "prefix":
            if not isinstance(value, str) or not any(
                value.startswith(p) for p in cvalue
            ):
                return f"{name}: prefix mismatch {cvalue}"
        elif ctype == "suffix":
            if not isinstance(value, str) or not any(
                value.endswith(s) for s in cvalue
            ):
                return f"{name}: suffix mismatch {cvalue}"
        elif ctype == "allowlist":
            if not any(fnmatch.fnmatch(str(value), p) for p in cvalue):
                return f"{name}: not in allowlist"
        elif ctype == "denylist":
            if any(fnmatch.fnmatch(str(value), p) for p in cvalue):
                return f"{name}: matches denylist"
        elif ctype == "max":
            if isinstance(value, (int, float)) and value > cvalue:
                return f"{name}: exceeds max {cvalue}"
        elif ctype == "min":
            if isinstance(value, (int, float)) and value < cvalue:
                return f"{name}: below min {cvalue}"
        elif ctype == "regex":
            if not isinstance(value, str) or not re.search(cvalue, value):
                return f"{name}: regex mismatch {cvalue}"
        elif ctype == "equals" and value != cvalue:
            return f"{name}: expected {cvalue!r}"
        return None


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
        conditions: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self.fail_closed = fail_closed
        self.consequential_operations = set(consequential_operations)
        self.max_risk_score = max_risk_score
        self.conditions = conditions or {}  # operation_id → conditions dict

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

        # Parameterized condition evaluation (DAE Standard precedence).
        op_conditions = self.conditions.get(tup.operation_id)
        if op_conditions:
            failures = ConditionEvaluator.evaluate(
                tup.to_dict(), op_conditions,
            )
            if failures:
                return PermitDecision(
                    decision="deny",
                    decision_id=decision_id,
                    tuple_hash=tuple_hash,
                    reason=f"condition_failed: {'; '.join(failures)}",
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
            # Provenance check: external untrusted data cannot grant authority
            if tup.provenance == Provenance.EXTERNAL_UNTRUSTED:
                return PermitDecision(
                    decision="deny",
                    decision_id=decision_id,
                    tuple_hash=tuple_hash,
                    reason="external_untrusted_cannot_authorize_consequential",
                )
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

    def __init__(
        self,
        receipt_store: ReceiptStore,
        mode: EnforcementMode = EnforcementMode.ENFORCE,
    ) -> None:
        self.receipt_store = receipt_store
        self.mode = mode

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
        # DISABLED mode: skip all enforcement (development only).
        if self.mode == EnforcementMode.DISABLED:
            return decision

        # OBSERVE mode: log but proceed regardless.
        if self.mode == EnforcementMode.OBSERVE:
            return decision

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
            return PermitDecision(
                decision="deny",
                decision_id=f"dec-{_uuid.uuid4().hex[:12]}",
                tuple_hash=tup.identity_hash(),
                reason="schema_hash_mismatch_tool_drift",
            )

        # Target binding: reject if the resolved target differs from the
        # admitted target (target swap attack).
        if observed_target_id and observed_target_id != tup.target_id:
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


class RuntimeOrchestrator:
    """Runtime state machine (from agent-policy-engine).

    Enforces legal state transitions. Authority issuance only
    allowed in EXECUTING state. Plan mutation after approval
    invalidates all tokens.
    """

    def __init__(self) -> None:
        self._state: RuntimeState = RuntimeState.IDLE

    @property
    def state(self) -> RuntimeState:
        return self._state

    def transition(self, new_state: RuntimeState) -> RuntimeState:
        """Transition to a new state. Raises on illegal transitions."""
        legal = _LEGAL_TRANSITIONS.get(self._state, set())
        if new_state not in legal:
            raise ValueError(
                f"Illegal state transition: {self._state.value} → {new_state.value}"
            )
        self._state = new_state
        return self._state

    def can_issue_authority(self) -> bool:
        """Authority issuance only allowed in EXECUTING state."""
        return self._state == RuntimeState.EXECUTING

    def reset(self) -> None:
        """Reset to IDLE state."""
        self._state = RuntimeState.IDLE


# ---------------------------------------------------------------------------
# Resource → Permission → Policy decomposition (adapted from Keycloak)
#
# Keycloak's authorization services use a three-tier model:
#   Resource → Permission → Policy → Decision
#
# - Resource: a protected object (MCP tool, file, endpoint, action).
# - Permission: binds a resource to one or more policies.
# - Policy: a rule that evaluates to allow/deny/ask.
#
# This is an ADDITIONAL layer on top of the existing PolicyDecisionPoint /
# PolicyEnforcementPoint. It does not replace them — when no explicit
# policies are registered for a resource, the ResourceRegistry falls back
# to the PolicyDecisionPoint for backward compatibility.
# ---------------------------------------------------------------------------

# Type alias: a PolicyDecision is the same PermitDecision used by the PDP.
PolicyDecision = PermitDecision

# A policy evaluator takes an AuthorizationTuple and returns a Decision.
PolicyEvaluator = Callable[[AuthorizationTuple], Decision]

# Aggregate logic for combining multiple policy decisions.
AggregateLogic = Literal["AND", "OR", "DENY_OVERRIDE"]

# Permission logic: positive (normal) or negative (inverted).
PermissionLogic = Literal["positive", "negative"]

# Protected resource types.
ResourceType = Literal["mcp_tool", "file", "endpoint", "action"]


@dataclass
class ProtectedResource:
    """A protected object in the authorization model.

    Adapted from Keycloak's ``Resource``: what is being protected
    (MCP tool name, file path, API endpoint, runtime action).
    """

    resource_id: str
    resource_type: ResourceType
    name: str
    description: str = ""


@dataclass
class Permission:
    """Binds a resource to one or more policies.

    Adapted from Keycloak's ``Permission``: links a resource to policy
    evaluators. The ``logic`` field (positive/negative) inverts the
    combined policy result — useful for "deny unless explicitly allowed"
    patterns.
    """

    permission_id: str
    resource_id: str
    policy_ids: list[str] = field(default_factory=list)
    logic: PermissionLogic = "positive"


def _aggregate_decisions(decisions: list[Decision], logic: AggregateLogic) -> Decision:
    """Combine multiple policy decisions using aggregate logic.

    - **AND** (unanimous): all must allow; any deny blocks; else ask.
    - **OR** (affirmative): any allow grants; all deny blocks; else ask.
    - **DENY_OVERRIDE**: any deny blocks; else any allow grants; else ask.
    """
    if not decisions:
        return "deny"
    if logic == "AND":
        if all(d == "allow" for d in decisions):
            return "allow"
        if "deny" in decisions:
            return "deny"
        return "ask"
    if logic == "OR":
        if any(d == "allow" for d in decisions):
            return "allow"
        if all(d == "deny" for d in decisions):
            return "deny"
        return "ask"
    # DENY_OVERRIDE
    if "deny" in decisions:
        return "deny"
    if any(d == "allow" for d in decisions):
        return "allow"
    return "ask"


def _invert_decision(d: Decision) -> Decision:
    """Invert a decision for negative-permission logic."""
    if d == "allow":
        return "deny"
    if d == "deny":
        return "allow"
    return "ask"


class ResourceRegistry:
    """Manages protected resources, permissions, and policy evaluators.

    Implements Keycloak's Resource → Permission → Policy decomposition.
    Resources are registered, permissions bind resources to policies, and
    ``evaluate_access`` combines policy results with aggregate logic
    (AND / OR / DENY_OVERRIDE).

    Backward compatible with ``PolicyDecisionPoint``: when no explicit
    policies are registered for a resource, the registry delegates to the
    PDP (if provided) or returns a deny.
    """

    def __init__(self, pdp: PolicyDecisionPoint | None = None) -> None:
        self._resources: dict[str, ProtectedResource] = {}
        self._permissions: dict[str, Permission] = {}
        self._policies: dict[str, PolicyEvaluator] = {}
        self._pdp = pdp

    def register_resource(self, resource: ProtectedResource) -> None:
        """Register a protected resource."""
        self._resources[resource.resource_id] = resource

    def get_resource(self, resource_id: str) -> ProtectedResource | None:
        """Look up a registered resource by ID."""
        return self._resources.get(resource_id)

    def bind_permission(self, permission: Permission) -> None:
        """Bind a permission (resource → policies) to the registry."""
        self._permissions[permission.permission_id] = permission

    def register_policy(self, policy_id: str, evaluator: PolicyEvaluator) -> None:
        """Register a policy evaluator by ID."""
        self._policies[policy_id] = evaluator

    def list_permissions_for_resource(self, resource_id: str) -> list[Permission]:
        """Return all permissions bound to a resource."""
        return [p for p in self._permissions.values() if p.resource_id == resource_id]

    def _evaluate_policy(
        self,
        policy_id: str,
        auth_tuple: AuthorizationTuple,
    ) -> Decision:
        """Evaluate a single policy, falling back to the PDP if unregistered."""
        evaluator = self._policies.get(policy_id)
        if evaluator is not None:
            return evaluator(auth_tuple)
        if self._pdp is not None:
            return self._pdp.decide(auth_tuple).decision
        return "deny"

    def evaluate_access(
        self,
        resource_id: str,
        auth_tuple: AuthorizationTuple,
        logic: AggregateLogic = "AND",
    ) -> PolicyDecision:
        """Evaluate access to a resource for an authorization tuple.

        Collects all permissions bound to the resource, evaluates each
        permission's policies, applies per-permission logic (positive /
        negative), then aggregates across permissions using ``logic``.

        Falls back to the ``PolicyDecisionPoint`` when no permissions are
        bound to the resource (backward compatibility).
        """
        tuple_hash = auth_tuple.identity_hash()
        decision_id = f"dec-{_uuid.uuid4().hex[:12]}"

        resource = self._resources.get(resource_id)
        if resource is None:
            return PermitDecision(
                decision="deny",
                decision_id=decision_id,
                tuple_hash=tuple_hash,
                reason="resource_not_found",
            )

        permissions = self.list_permissions_for_resource(resource_id)
        if not permissions:
            # Backward compatibility: delegate to PDP if available.
            if self._pdp is not None:
                return self._pdp.decide(auth_tuple)
            return PermitDecision(
                decision="deny",
                decision_id=decision_id,
                tuple_hash=tuple_hash,
                reason="no_permissions_bound",
            )

        # Collect the combined decision from each permission.
        permission_decisions: list[Decision] = []
        for perm in permissions:
            policy_decisions = [
                self._evaluate_policy(pid, auth_tuple) for pid in perm.policy_ids
            ]
            # Aggregate within the permission using the same logic.
            perm_result = _aggregate_decisions(policy_decisions, logic)
            if perm.logic == "negative":
                perm_result = _invert_decision(perm_result)
            permission_decisions.append(perm_result)

        final = _aggregate_decisions(permission_decisions, logic)
        return PermitDecision(
            decision=final,
            decision_id=decision_id,
            tuple_hash=tuple_hash,
            reason=f"resource:{resource_id}:logic:{logic}",
        )
