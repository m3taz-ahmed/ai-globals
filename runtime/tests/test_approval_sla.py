"""Tests for runtime/approval_sla.py — SLA management + decision deltas."""

from __future__ import annotations

import time

import pytest

from runtime.approval_sla import (
    ApprovalSlaManager,
    DecisionDelta,
    SlaAction,
    SlaPolicy,
)


def _mgr(**kw) -> ApprovalSlaManager:
    kw.setdefault("timeout_seconds", 3600)
    return ApprovalSlaManager(SlaPolicy(**kw))


def _expire(state, seconds: float = 9999):
    """Push created_at into the past (deterministic timeout)."""
    state.created_at = time.time() - seconds


class TestPolicy:
    def test_timeout_required(self):
        with pytest.raises(ValueError, match="positive"):
            SlaPolicy(timeout_seconds=0)

    def test_escalate_must_precede_timeout(self):
        with pytest.raises(ValueError, match="less than"):
            SlaPolicy(timeout_seconds=100, escalate_after=100)
        with pytest.raises(ValueError, match="less than"):
            SlaPolicy(timeout_seconds=100, escalate_after=200)

    def test_reminder_positive(self):
        with pytest.raises(ValueError, match="positive"):
            SlaPolicy(timeout_seconds=100, reminder_interval=-1)


class TestRegisterAndCheck:
    def test_register_default_policy(self):
        mgr = _mgr()
        state = mgr.register("req-1")
        assert state.request_id == "req-1"
        assert not state.escalated and not state.auto_resolved

    def test_check_unknown(self):
        assert _mgr().check("ghost") is None

    def test_check_within_timeout(self):
        mgr = _mgr()
        mgr.register("req-1")
        assert mgr.check("req-1") is None

    def test_check_timeout_no_action(self):
        mgr = _mgr()  # auto_action=None
        state = mgr.register("req-1")
        _expire(state)
        assert mgr.check("req-1") is None  # breach recorded but no action

    def test_auto_deny_on_timeout(self):
        mgr = _mgr(auto_action=SlaAction.AUTO_DENY)
        state = mgr.register("req-1")
        _expire(state)
        assert mgr.check("req-1") is SlaAction.AUTO_DENY

    def test_auto_approve(self):
        mgr = _mgr(auto_action=SlaAction.AUTO_APPROVE)
        state = mgr.register("req-1")
        _expire(state)
        assert mgr.check("req-1") is SlaAction.AUTO_APPROVE

    def test_escalate_before_timeout(self):
        mgr = _mgr(escalate_after=100, auto_action=SlaAction.AUTO_DENY)
        state = mgr.register("req-1")
        _expire(state, 200)  # past escalate_after, before timeout
        assert mgr.check("req-1") is SlaAction.ESCALATE

    def test_escalate_only_once(self):
        mgr = _mgr(escalate_after=100, auto_action=SlaAction.AUTO_DENY)
        state = mgr.register("req-1")
        _expire(state, 200)
        mgr.process("req-1")  # applies escalate
        state.escalated = True
        # now elapsed 200 < timeout 3600, escalated -> remind/None
        assert mgr.check("req-1") is None

    def test_reminder_fires(self):
        mgr = _mgr(reminder_interval=100)
        state = mgr.register("req-1")
        _expire(state, 150)  # past reminder interval, before timeout
        assert mgr.check("req-1") is SlaAction.REMIND

    def test_reminder_not_immediate(self):
        mgr = _mgr(reminder_interval=3600)
        mgr.register("req-1")
        assert mgr.check("req-1") is None


class TestProcess:
    def test_process_unknown(self):
        assert _mgr().process("ghost") == {"request_id": "ghost", "action": None}

    def test_process_no_action(self):
        mgr = _mgr()
        mgr.register("req-1")
        assert mgr.process("req-1") == {"request_id": "req-1", "action": None}

    def test_process_escalate_marks_state(self):
        mgr = _mgr(escalate_after=100)
        state = mgr.register("req-1")
        _expire(state, 200)
        r = mgr.process("req-1")
        assert r["action"] == "escalate" and r["escalated"] is True

    def test_process_remind_updates_timestamp(self):
        mgr = _mgr(reminder_interval=100)
        state = mgr.register("req-1")
        _expire(state, 150)
        r = mgr.process("req-1")
        assert r["action"] == "remind"
        assert state.last_reminder is not None

    def test_process_auto_deny_resolves(self):
        mgr = _mgr(auto_action=SlaAction.AUTO_DENY)
        state = mgr.register("req-1")
        _expire(state)
        r = mgr.process("req-1")
        assert r["action"] == "auto_deny" and r["auto_resolved"] is True
        # Once auto-resolved, check() returns None
        assert mgr.check("req-1") is None


class TestDecisionDelta:
    def test_identical_no_changes(self):
        mgr = _mgr()
        d = mgr.record_decision("r1", {"a": 1, "b": 2}, {"a": 1, "b": 2}, "rev")
        assert d.field_changes == []

    def test_modified_field(self):
        mgr = _mgr()
        d = mgr.record_decision("r1", {"a": 1}, {"a": 2}, "rev")
        assert d.field_changes == [
            {"field": "a", "change_type": "modified", "proposed": 1, "approved": 2}]

    def test_added_removed(self):
        mgr = _mgr()
        d = mgr.record_decision("r1", {"old": 1}, {"new": 2}, "rev")
        types = {c["change_type"] for c in d.field_changes}
        assert types == {"added", "removed"}

    def test_correction_rate(self):
        mgr = _mgr()
        mgr.record_decision("r1", {"a": 1}, {"a": 1}, "rev")   # no change
        mgr.record_decision("r2", {"a": 1}, {"a": 2}, "rev")   # corrected
        assert mgr.correction_rate() == 50.0

    def test_correction_rate_empty(self):
        assert _mgr().correction_rate() == 0.0

    def test_get_deltas_limit(self):
        mgr = _mgr()
        for i in range(5):
            mgr.record_decision(f"r{i}", {"x": i}, {"x": i}, "rev")
        assert len(mgr.get_deltas(limit=3)) == 3
        assert len(mgr.get_deltas(limit=0)) == 5  # 0/negative = all

    def test_escalation_rate(self):
        mgr = _mgr(escalate_after=100)
        s1 = mgr.register("r1")
        _expire(s1, 200)
        mgr.register("r2")
        mgr.process("r1")
        assert mgr.escalation_rate() == 50.0

    def test_escalation_rate_empty(self):
        assert _mgr().escalation_rate() == 0.0

    def test_reregister_overwrites(self):
        mgr = _mgr()
        s1 = mgr.register("r1")
        s1.escalated = True
        s2 = mgr.register("r1")  # fresh state
        assert s2.escalated is False

    def test_delta_fields(self):
        mgr = _mgr()
        d = mgr.record_decision("r1", {"a": 1}, {"a": 1}, "alice")
        assert isinstance(d, DecisionDelta)
        assert d.reviewer == "alice" and d.timestamp > 0
