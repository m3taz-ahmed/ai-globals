"""Tests for BudgetWindow tracking pattern (from MLflow).

Covers BudgetWindow, BudgetAction, BudgetTargetScope, BudgetWindowManager,
BudgetAlert, and BudgetAlerter.
"""

from __future__ import annotations

import time
import uuid

import pytest

from runtime.budget import (
    BudgetAction,
    BudgetTargetScope,
    BudgetWindow,
    BudgetWindowManager,
    make_window,
)
from runtime.budget_anomaly import BudgetAlert, BudgetAlerter

# ---------------------------------------------------------------------------
# BudgetAction enum
# ---------------------------------------------------------------------------


class TestBudgetAction:
    def test_alert_value(self) -> None:
        assert BudgetAction.ALERT.value == "alert"

    def test_reject_value(self) -> None:
        assert BudgetAction.REJECT.value == "reject"

    def test_warn_value(self) -> None:
        assert BudgetAction.WARN.value == "warn"

    def test_is_str_enum(self) -> None:
        assert isinstance(BudgetAction.ALERT, str)


# ---------------------------------------------------------------------------
# BudgetTargetScope enum
# ---------------------------------------------------------------------------


class TestBudgetTargetScope:
    def test_session_value(self) -> None:
        assert BudgetTargetScope.SESSION.value == "session"

    def test_agent_value(self) -> None:
        assert BudgetTargetScope.AGENT.value == "agent"

    def test_global_value(self) -> None:
        assert BudgetTargetScope.GLOBAL.value == "global"


# ---------------------------------------------------------------------------
# BudgetWindow construction and properties
# ---------------------------------------------------------------------------


class TestBudgetWindow:
    def _make_window(
        self, spend: float = 0.0, limit: float = 100.0
    ) -> BudgetWindow:
        now = time.time()
        return BudgetWindow(
            window_id=str(uuid.uuid4()),
            scope=BudgetTargetScope.SESSION,
            scope_id="sess-1",
            period="daily",
            start_time=now,
            end_time=now + 86400.0,
            spend=spend,
            limit=limit,
            action=BudgetAction.WARN,
        )

    def test_construction_defaults(self) -> None:
        now = time.time()
        w = BudgetWindow(
            window_id="w1",
            scope=BudgetTargetScope.GLOBAL,
            scope_id="global",
            period="daily",
            start_time=now,
            end_time=now + 86400.0,
        )
        assert w.spend == 0.0
        assert w.limit == 0.0
        assert w.action == BudgetAction.WARN
        assert w.is_active is True

    def test_remaining_property(self) -> None:
        w = self._make_window(spend=30.0, limit=100.0)
        assert w.remaining == 70.0

    def test_remaining_clamped_to_zero(self) -> None:
        w = self._make_window(spend=150.0, limit=100.0)
        assert w.remaining == 0.0

    def test_utilization_property(self) -> None:
        w = self._make_window(spend=40.0, limit=100.0)
        assert w.utilization == pytest.approx(0.4)

    def test_utilization_zero_limit_returns_zero(self) -> None:
        w = self._make_window(spend=10.0, limit=0.0)
        assert w.utilization == 0.0

    def test_is_exceeded_true_at_limit(self) -> None:
        w = self._make_window(spend=100.0, limit=100.0)
        assert w.is_exceeded is True

    def test_is_exceeded_false_under_limit(self) -> None:
        w = self._make_window(spend=50.0, limit=100.0)
        assert w.is_exceeded is False

    def test_is_exceeded_false_when_limit_zero(self) -> None:
        w = self._make_window(spend=100.0, limit=0.0)
        assert w.is_exceeded is False


# ---------------------------------------------------------------------------
# BudgetWindowManager
# ---------------------------------------------------------------------------


class TestBudgetWindowManager:
    def _make_manager_with_window(
        self,
        limit: float = 100.0,
        spend: float = 0.0,
        action: BudgetAction = BudgetAction.WARN,
        scope: BudgetTargetScope = BudgetTargetScope.SESSION,
        scope_id: str = "sess-1",
    ) -> tuple[BudgetWindowManager, BudgetWindow]:
        mgr = BudgetWindowManager()
        w = make_window(scope, scope_id, period="daily", limit=limit, action=action)
        w.spend = spend
        mgr.register_window(w)
        return mgr, w

    def test_register_window_stores_window(self) -> None:
        mgr, w = self._make_manager_with_window()
        assert w.window_id in mgr._windows

    def test_check_budget_limit_warn_when_under_limit(self) -> None:
        mgr, _ = self._make_manager_with_window(limit=100.0, spend=10.0)
        action = mgr.check_budget_limit(BudgetTargetScope.SESSION, "sess-1", 5.0)
        assert action == BudgetAction.WARN

    def test_check_budget_limit_reject_when_over_limit(self) -> None:
        mgr, _ = self._make_manager_with_window(
            limit=100.0, spend=95.0, action=BudgetAction.REJECT
        )
        action = mgr.check_budget_limit(BudgetTargetScope.SESSION, "sess-1", 10.0)
        assert action == BudgetAction.REJECT

    def test_check_budget_limit_alert_at_threshold(self) -> None:
        # spend=70, amount=15 → projected=85 → 85% >= 80% threshold
        mgr, _ = self._make_manager_with_window(
            limit=100.0, spend=70.0, action=BudgetAction.ALERT
        )
        action = mgr.check_budget_limit(BudgetTargetScope.SESSION, "sess-1", 15.0)
        assert action == BudgetAction.ALERT

    def test_check_budget_limit_warn_when_no_matching_window(self) -> None:
        mgr, _ = self._make_manager_with_window(scope_id="sess-1")
        action = mgr.check_budget_limit(BudgetTargetScope.SESSION, "other", 5.0)
        assert action == BudgetAction.WARN

    def test_on_complete_records_actual_cost(self) -> None:
        mgr, w = self._make_manager_with_window(limit=100.0, spend=10.0)
        mgr.on_complete(BudgetTargetScope.SESSION, "sess-1", 25.0)
        assert w.spend == 35.0

    def test_on_complete_fires_alert_callback_on_threshold(self) -> None:
        mgr, w = self._make_manager_with_window(limit=100.0, spend=70.0)
        called: list[BudgetWindow] = []
        mgr.register_alert_callback(lambda win: called.append(win))
        # Adding 15 → spend=85 → crosses 80% threshold
        mgr.on_complete(BudgetTargetScope.SESSION, "sess-1", 15.0)
        assert len(called) == 1
        assert called[0].window_id == w.window_id

    def test_register_alert_callback_invoked_on_exceed(self) -> None:
        mgr, _w = self._make_manager_with_window(limit=100.0, spend=90.0)
        called: list[BudgetWindow] = []
        mgr.register_alert_callback(lambda win: called.append(win))
        # Adding 15 → spend=105 → newly exceeded
        mgr.on_complete(BudgetTargetScope.SESSION, "sess-1", 15.0)
        assert len(called) >= 1

    def test_backfill_from_audit_reconstructs_spend(self) -> None:
        mgr, w = self._make_manager_with_window(limit=100.0, spend=0.0)
        entries = [
            {
                "scope": "session",
                "scope_id": "sess-1",
                "cost": 10.0,
                "timestamp": w.start_time + 100,
            },
            {
                "scope": "session",
                "scope_id": "sess-1",
                "cost": 20.0,
                "timestamp": w.start_time + 200,
            },
            {
                "scope": "session",
                "scope_id": "sess-1",
                "cost": 5.0,
                "timestamp": w.end_time + 999,  # outside window
            },
        ]
        mgr.backfill_from_audit(entries)
        assert w.spend == pytest.approx(30.0)

    def test_backfill_ignores_unknown_scope(self) -> None:
        mgr, w = self._make_manager_with_window(limit=100.0, spend=0.0)
        entries = [
            {
                "scope": "unknown_scope",
                "scope_id": "sess-1",
                "cost": 10.0,
                "timestamp": w.start_time + 100,
            },
        ]
        mgr.backfill_from_audit(entries)
        assert w.spend == 0.0

    def test_get_active_windows_returns_only_active(self) -> None:
        mgr = BudgetWindowManager()
        w1 = make_window(BudgetTargetScope.SESSION, "s1", limit=100.0)
        w2 = make_window(BudgetTargetScope.SESSION, "s2", limit=100.0)
        w2.is_active = False
        mgr.register_window(w1)
        mgr.register_window(w2)
        active = mgr.get_active_windows()
        assert len(active) == 1
        assert active[0].window_id == w1.window_id

    def test_get_active_windows_excludes_expired(self) -> None:
        mgr = BudgetWindowManager()
        now = time.time()
        w = BudgetWindow(
            window_id="expired",
            scope=BudgetTargetScope.SESSION,
            scope_id="s1",
            period="daily",
            start_time=now - 200,
            end_time=now - 100,  # already ended
            limit=100.0,
        )
        mgr.register_window(w)
        assert len(mgr.get_active_windows()) == 0

    def test_maybe_refresh_policies_skips_when_fresh(self) -> None:
        mgr = BudgetWindowManager()
        # Immediately after init, policies are fresh
        assert mgr.maybe_refresh_policies() is False

    def test_maybe_refresh_policies_refreshes_when_stale(self) -> None:
        mgr = BudgetWindowManager()
        # Simulate stale by backdating last refresh
        mgr._last_policy_refresh = time.time() - 400.0
        assert mgr.maybe_refresh_policies() is True
        # Now fresh again
        assert mgr.maybe_refresh_policies() is False

    def test_check_budget_limit_expires_old_windows(self) -> None:
        mgr = BudgetWindowManager()
        now = time.time()
        w = BudgetWindow(
            window_id="old",
            scope=BudgetTargetScope.SESSION,
            scope_id="s1",
            period="daily",
            start_time=now - 200,
            end_time=now - 100,  # expired
            limit=100.0,
            action=BudgetAction.REJECT,
        )
        mgr.register_window(w)
        # Expired window should not cause REJECT
        action = mgr.check_budget_limit(BudgetTargetScope.SESSION, "s1", 50.0)
        assert action == BudgetAction.WARN
        assert w.is_active is False


# ---------------------------------------------------------------------------
# BudgetAlert construction
# ---------------------------------------------------------------------------


class TestBudgetAlert:
    def test_construction(self) -> None:
        alert = BudgetAlert(
            alert_id="a1",
            window_id="w1",
            scope=BudgetTargetScope.SESSION,
            scope_id="sess-1",
            utilization=0.85,
            threshold=0.8,
            message="Budget at 85%",
            timestamp=time.time(),
            action_taken=BudgetAction.ALERT,
        )
        assert alert.alert_id == "a1"
        assert alert.window_id == "w1"
        assert alert.scope == BudgetTargetScope.SESSION
        assert alert.utilization == pytest.approx(0.85)
        assert alert.threshold == pytest.approx(0.8)
        assert alert.action_taken == BudgetAction.ALERT


# ---------------------------------------------------------------------------
# BudgetAlerter
# ---------------------------------------------------------------------------


class TestBudgetAlerter:
    def _make_window(self, spend: float, limit: float) -> BudgetWindow:
        now = time.time()
        return BudgetWindow(
            window_id=str(uuid.uuid4()),
            scope=BudgetTargetScope.SESSION,
            scope_id="sess-1",
            period="daily",
            start_time=now,
            end_time=now + 86400.0,
            spend=spend,
            limit=limit,
            action=BudgetAction.ALERT,
        )

    def test_check_thresholds_at_50_percent(self) -> None:
        alerter = BudgetAlerter()
        w = self._make_window(spend=50.0, limit=100.0)
        alerts = alerter.check_thresholds(w)
        thresholds = [a.threshold for a in alerts]
        assert 0.5 in thresholds

    def test_check_thresholds_at_80_percent(self) -> None:
        alerter = BudgetAlerter()
        w = self._make_window(spend=80.0, limit=100.0)
        alerts = alerter.check_thresholds(w)
        thresholds = [a.threshold for a in alerts]
        assert 0.5 in thresholds
        assert 0.8 in thresholds

    def test_check_thresholds_at_90_percent(self) -> None:
        alerter = BudgetAlerter()
        w = self._make_window(spend=90.0, limit=100.0)
        alerts = alerter.check_thresholds(w)
        thresholds = [a.threshold for a in alerts]
        assert 0.9 in thresholds

    def test_check_thresholds_at_100_percent(self) -> None:
        alerter = BudgetAlerter()
        w = self._make_window(spend=100.0, limit=100.0)
        alerts = alerter.check_thresholds(w)
        thresholds = [a.threshold for a in alerts]
        assert 1.0 in thresholds

    def test_check_thresholds_no_alert_under_50(self) -> None:
        alerter = BudgetAlerter()
        w = self._make_window(spend=40.0, limit=100.0)
        alerts = alerter.check_thresholds(w)
        assert len(alerts) == 0

    def test_check_thresholds_dedupes_per_window(self) -> None:
        alerter = BudgetAlerter()
        w = self._make_window(spend=85.0, limit=100.0)
        first = alerter.check_thresholds(w)
        second = alerter.check_thresholds(w)
        assert len(first) >= 2  # 50% + 80%
        assert len(second) == 0  # already fired

    def test_send_alerts_calls_webhooks(self) -> None:
        alerter = BudgetAlerter()
        received: list[BudgetAlert] = []
        alerter.register_webhook(lambda a: received.append(a))
        alert = BudgetAlert(
            alert_id="a1",
            window_id="w1",
            scope=BudgetTargetScope.SESSION,
            scope_id="s1",
            utilization=0.8,
            threshold=0.8,
            message="test",
            timestamp=time.time(),
            action_taken=BudgetAction.ALERT,
        )
        alerter.send_alerts([alert])
        assert len(received) == 1
        assert received[0].alert_id == "a1"

    def test_send_alerts_calls_multiple_webhooks(self) -> None:
        alerter = BudgetAlerter()
        r1: list[BudgetAlert] = []
        r2: list[BudgetAlert] = []
        alerter.register_webhook(lambda a: r1.append(a))
        alerter.register_webhook(lambda a: r2.append(a))
        alert = BudgetAlert(
            alert_id="a1",
            window_id="w1",
            scope=BudgetTargetScope.GLOBAL,
            scope_id="global",
            utilization=1.0,
            threshold=1.0,
            message="exceeded",
            timestamp=time.time(),
            action_taken=BudgetAction.REJECT,
        )
        alerter.send_alerts([alert])
        assert len(r1) == 1
        assert len(r2) == 1

    def test_register_webhook_appends(self) -> None:
        alerter = BudgetAlerter()
        alerter.register_webhook(lambda a: None)
        alerter.register_webhook(lambda a: None)
        assert len(alerter._webhooks) == 2


# ---------------------------------------------------------------------------
# make_window helper
# ---------------------------------------------------------------------------


class TestMakeWindow:
    def test_make_window_creates_valid_window(self) -> None:
        w = make_window(
            BudgetTargetScope.AGENT, "agent-1", period="hourly", limit=50.0
        )
        assert w.scope == BudgetTargetScope.AGENT
        assert w.scope_id == "agent-1"
        assert w.period == "hourly"
        assert w.limit == 50.0
        assert w.spend == 0.0
        assert w.is_active is True
        assert w.end_time > w.start_time

    def test_make_window_custom_id(self) -> None:
        w = make_window(
            BudgetTargetScope.GLOBAL, "global", period="daily", window_id="custom-1"
        )
        assert w.window_id == "custom-1"


# ---------------------------------------------------------------------------
# Integration: BudgetManager + BudgetWindowManager
# ---------------------------------------------------------------------------


class TestBudgetManagerWindowIntegration:
    def test_window_manager_optional_default_none(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        from runtime.budget import BudgetManager

        mgr = BudgetManager(tmp_path)
        assert mgr.window_manager is None

    def test_window_reject_blocks_check(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        from runtime.budget import Budget, BudgetManager

        mgr = BudgetManager(tmp_path)
        mgr.set_budget("session", Budget(max_cost_usd=100.0, on_exceed="warn"))
        wm = BudgetWindowManager()
        w = make_window(
            BudgetTargetScope.SESSION, "session", limit=10.0, action=BudgetAction.REJECT
        )
        w.spend = 9.0
        wm.register_window(w)
        mgr.window_manager = wm
        result = mgr.check("session", cost=5.0)
        assert result["ok"] is False
        assert result["action"] == "block"
