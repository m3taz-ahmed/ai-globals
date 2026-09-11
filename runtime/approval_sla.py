#!/usr/bin/env python3
"""Approval SLA management with auto-degradation and decision delta tracking.

Inspired by sphinx's approval lifecycle: every human-in-the-loop (HITL)
approval request is registered with an SLA policy. If the reviewer does
not respond within the configured timeout, the system can
auto-escalate, auto-approve, or auto-deny based on policy — preventing
agent pipelines from stalling indefinitely on unresponsive reviewers.

Additionally, every decision is tracked as a :class:`DecisionDelta`:
the difference between what the agent *proposed* and what the reviewer
*approved*. This provides governance metrics showing how often
reviewers modify agent proposals (correction rate) and how often SLA
timeouts force auto-actions (escalation rate).

Usage::

    from runtime.approval_sla import ApprovalSlaManager, SlaPolicy, SlaAction
    mgr = ApprovalSlaManager(SlaPolicy(timeout_seconds=3600, auto_action=SlaAction.AUTO_DENY))
    state = mgr.register("req-123")
    action = mgr.check("req-123")  # None until timeout
    delta = mgr.record_decision("req-123", proposed, approved, "reviewer-1")
    print(mgr.correction_rate())
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

_logger = logging.getLogger(__name__)


class SlaAction(str, Enum):
    """Actions the SLA manager can take when a timeout is reached."""

    ESCALATE = "escalate"      # Notify a higher-priority channel
    AUTO_APPROVE = "auto_approve"  # Approve automatically (fail-open)
    AUTO_DENY = "auto_deny"   # Deny automatically (fail-closed)
    REMIND = "remind"          # Send a reminder notification


@dataclass
class SlaPolicy:
    """SLA policy for an approval request.

    Attributes:
        timeout_seconds: Maximum time before the SLA action triggers.
        escalate_after: If set, escalate after this many seconds
            (before the full timeout). ``None`` = no separate escalation.
        auto_action: Action to take when the timeout is reached.
            ``None`` means no automatic action (just record the breach).
        reminder_interval: If set, send a reminder every this many
            seconds while the request is pending. ``None`` = no reminders.
    """

    timeout_seconds: float
    escalate_after: float | None = None
    auto_action: SlaAction | None = None
    reminder_interval: float | None = None

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.escalate_after is not None and self.escalate_after >= self.timeout_seconds:
            raise ValueError("escalate_after must be less than timeout_seconds")
        if self.reminder_interval is not None and self.reminder_interval <= 0:
            raise ValueError("reminder_interval must be positive")


@dataclass
class SlaState:
    """Runtime state of an SLA-tracked approval request.

    Attributes:
        request_id: The approval request identifier.
        created_at: When the request was registered (epoch seconds).
        last_reminder: Timestamp of the last reminder sent, if any.
        escalated: Whether the request has been escalated.
        auto_resolved: Whether the request was auto-resolved by SLA.
    """

    request_id: str
    created_at: float
    last_reminder: float | None = None
    escalated: bool = False
    auto_resolved: bool = False


@dataclass
class DecisionDelta:
    """Difference between proposed and approved payloads.

    Tracks what the agent proposed vs what the reviewer actually
    approved, enabling governance metrics on reviewer correction rates.

    Attributes:
        request_id: The approval request identifier.
        proposed_payload: What the agent proposed.
        approved_payload: What the reviewer approved.
        field_changes: List of per-field change records.
        reviewer: Who made the decision.
        timestamp: When the decision was recorded.
    """

    request_id: str
    proposed_payload: dict[str, Any]
    approved_payload: dict[str, Any]
    field_changes: list[dict[str, Any]]
    reviewer: str
    timestamp: float = field(default_factory=time.time)


class ApprovalSlaManager:
    """Manages SLA policies and decision tracking for approval requests.

    Thread-safe via a re-entrant lock. Each request is registered with
    a policy (or the default). ``check()`` evaluates whether the SLA
    timeout has been reached and returns the action to take.
    ``process()`` applies the action (marking escalation, setting
    auto-resolved). ``record_decision()`` captures the proposed-vs-
    approved delta for governance reporting.
    """

    def __init__(self, default_policy: SlaPolicy) -> None:
        self._default_policy = default_policy
        self._lock = threading.RLock()
        self._states: dict[str, SlaState] = {}
        self._policies: dict[str, SlaPolicy] = {}
        self._deltas: list[DecisionDelta] = []

    def register(
        self,
        request_id: str,
        policy: SlaPolicy | None = None,
    ) -> SlaState:
        """Register a new approval request for SLA tracking.

        If *policy* is ``None``, the manager's default policy is used.
        Re-registering an existing request_id overwrites the prior state.
        """
        effective = policy or self._default_policy
        state = SlaState(
            request_id=request_id,
            created_at=time.time(),
        )
        with self._lock:
            self._states[request_id] = state
            self._policies[request_id] = effective
        _logger.debug(
            "Registered SLA for %s: timeout=%.0fs action=%s",
            request_id[:8], effective.timeout_seconds,
            effective.auto_action.value if effective.auto_action else "none",
        )
        return state

    def check(self, request_id: str) -> SlaAction | None:
        """Check if the SLA timeout has been reached for *request_id*.

        Returns the action to take (``SlaAction``), or ``None`` if the
        SLA has not been breached or the request is unknown.
        """
        with self._lock:
            state = self._states.get(request_id)
            policy = self._policies.get(request_id)
            if state is None or policy is None or state.auto_resolved:
                return None
            return self._evaluate_sla(state, policy)

    def _evaluate_sla(self, state: SlaState, policy: SlaPolicy) -> SlaAction | None:
        """Evaluate SLA conditions and return the action to take."""
        elapsed = time.time() - state.created_at
        if self._should_escalate(policy, elapsed, state.escalated):
            return SlaAction.ESCALATE
        if self._should_remind(policy, state):
            return SlaAction.REMIND
        if elapsed >= policy.timeout_seconds:
            return policy.auto_action
        return None

    @staticmethod
    def _should_escalate(policy: SlaPolicy, elapsed: float, escalated: bool) -> bool:
        """Check if escalation action should trigger."""
        return (
            policy.escalate_after is not None
            and elapsed >= policy.escalate_after
            and not escalated
        )

    @staticmethod
    def _should_remind(policy: SlaPolicy, state: SlaState) -> bool:
        """Check if a reminder should be sent."""
        if policy.reminder_interval is None:
            return False
        last = state.last_reminder or state.created_at
        return time.time() - last >= policy.reminder_interval

    def process(self, request_id: str) -> dict[str, Any]:
        """Process the SLA for *request_id* and return the action taken.

        This is the side-effecting counterpart to ``check()``: it
        evaluates the SLA, applies any state changes (marking
        escalation, updating reminder timestamp, setting auto_resolved),
        and returns a dict describing what happened.
        """
        action = self.check(request_id)
        if action is None:
            return {"request_id": request_id, "action": None}
        with self._lock:
            state = self._states.get(request_id)
            if state is None:
                return {"request_id": request_id, "action": None}
            now = time.time()
            self._apply_action(state, action, request_id, now)
            return {
                "request_id": request_id,
                "action": action.value,
                "elapsed_seconds": round(now - state.created_at, 1),
                "escalated": state.escalated,
                "auto_resolved": state.auto_resolved,
            }

    @staticmethod
    def _apply_action(
        state: SlaState, action: SlaAction, request_id: str, now: float,
    ) -> None:
        """Apply SLA action side-effects to *state*."""
        if action is SlaAction.ESCALATE:
            state.escalated = True
            _logger.info("SLA escalation for %s", request_id[:8])
        elif action is SlaAction.REMIND:
            state.last_reminder = now
            _logger.debug("SLA reminder for %s", request_id[:8])
        elif action in (SlaAction.AUTO_APPROVE, SlaAction.AUTO_DENY):
            state.auto_resolved = True
            _logger.warning(
                "SLA auto-%s for %s after %.0fs",
                action.value, request_id[:8], now - state.created_at,
            )

    def record_decision(
        self,
        request_id: str,
        proposed: dict[str, Any],
        approved: dict[str, Any],
        reviewer: str,
    ) -> DecisionDelta:
        """Record the delta between proposed and approved payloads.

        Computes per-field changes (added, removed, modified) and
        stores the :class:`DecisionDelta` for governance metrics.
        """
        changes = self._compute_field_changes(proposed, approved)
        delta = DecisionDelta(
            request_id=request_id,
            proposed_payload=proposed,
            approved_payload=approved,
            field_changes=changes,
            reviewer=reviewer,
        )
        with self._lock:
            self._deltas.append(delta)
        _logger.debug(
            "Decision recorded for %s by %s: %d field changes",
            request_id[:8], reviewer, len(changes),
        )
        return delta

    def get_deltas(self, limit: int = 100) -> list[DecisionDelta]:
        """Return the most recent decision deltas (governance metrics)."""
        with self._lock:
            if limit <= 0:
                return list(self._deltas)
            return list(self._deltas[-limit:])

    def escalation_rate(self) -> float:
        """Return the percentage of requests that were escalated.

        Returns 0.0 if no requests have been registered.
        """
        with self._lock:
            total = len(self._states)
            if total == 0:
                return 0.0
            escalated = sum(1 for s in self._states.values() if s.escalated)
            return round(escalated / total * 100, 2)

    def correction_rate(self) -> float:
        """Return the percentage of decisions where approved != proposed.

        A "correction" is any decision where the reviewer modified at
        least one field. Returns 0.0 if no decisions have been recorded.
        """
        with self._lock:
            total = len(self._deltas)
            if total == 0:
                return 0.0
            corrected = sum(1 for d in self._deltas if d.field_changes)
            return round(corrected / total * 100, 2)

    @staticmethod
    def _compute_field_changes(
        proposed: dict[str, Any],
        approved: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Compute per-field differences between proposed and approved.

        Returns a list of change records, each with ``field``,
        ``change_type`` (``added`` / ``removed`` / ``modified``),
        ``proposed`` and ``approved`` values.
        """
        changes: list[dict[str, Any]] = []
        all_keys = sorted(set(proposed) | set(approved))
        for key in all_keys:
            change = ApprovalSlaManager._field_change(key, proposed, approved)
            if change is not None:
                changes.append(change)
        return changes

    @staticmethod
    def _field_change(
        key: str,
        proposed: dict[str, Any],
        approved: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Compute a single field's change record, or None if unchanged."""
        in_p, in_a = key in proposed, key in approved
        if in_p and not in_a:
            return {"field": key, "change_type": "removed",
                    "proposed": proposed[key], "approved": None}
        if in_a and not in_p:
            return {"field": key, "change_type": "added",
                    "proposed": None, "approved": approved[key]}
        if in_p and in_a and proposed[key] != approved[key]:
            return {"field": key, "change_type": "modified",
                    "proposed": proposed[key], "approved": approved[key]}
        return None
