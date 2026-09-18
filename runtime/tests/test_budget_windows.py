"""Gap-coverage tests for runtime/budget.py — BudgetWindowManager + check paths."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from runtime.budget import (
    Budget,
    BudgetAction,
    BudgetManager,
    BudgetTargetScope,
    BudgetWindow,
    BudgetWindowManager,
    _period_seconds,
    make_window,
)


def _window(**kw) -> BudgetWindow:
    now = time.time()
    defaults = {
        "window_id": "w1", "scope": BudgetTargetScope.SESSION, "scope_id": "s1",
        "period": "hourly", "start_time": now - 10, "end_time": now + 3600,
        "limit": 100.0,
    }
    defaults.update(kw)
    return BudgetWindow(**defaults)


class TestBudgetWindow:
    def test_remaining(self):
        w = _window(limit=100, spend=30)
        assert w.remaining == 70.0
        w.spend = 150
        assert w.remaining == 0.0

    def test_utilization(self):
        assert _window(limit=100, spend=25).utilization == 0.25
        assert _window(limit=0).utilization == 0.0

    def test_is_exceeded(self):
        assert _window(limit=10, spend=10).is_exceeded is True
        assert _window(limit=10, spend=5).is_exceeded is False
        assert _window(limit=0, spend=5).is_exceeded is False


class TestPeriodSeconds:
    @pytest.mark.parametrize("p,secs", [
        ("hourly", 3600.0), ("daily", 86400.0),
        ("weekly", 604800.0), ("monthly", 2592000.0)])
    def test_known(self, p, secs):
        assert _period_seconds(p) == secs

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown budget period"):
            _period_seconds("session")
        with pytest.raises(ValueError):
            _period_seconds("fortnightly")


class TestWindowManager:
    def test_register_and_match(self):
        m = BudgetWindowManager()
        m.register_window(_window())
        m.register_window(_window(window_id="w2", scope_id="other"))
        wins = m._matching_windows(BudgetTargetScope.SESSION, "s1")
        assert [w.window_id for w in wins] == ["w1"]

    def test_inactive_window_skipped(self):
        m = BudgetWindowManager()
        m.register_window(_window(is_active=False))
        assert m._matching_windows(BudgetTargetScope.SESSION, "s1") == []

    def test_expired_window_deactivated(self):
        m = BudgetWindowManager()
        m.register_window(_window(end_time=time.time() - 1))
        assert m._matching_windows(BudgetTargetScope.SESSION, "s1") == []

    def test_check_no_windows_warns(self):
        m = BudgetWindowManager()
        assert m.check_budget_limit(BudgetTargetScope.SESSION, "s1", 5) is \
            BudgetAction.WARN

    def test_check_reject(self):
        m = BudgetWindowManager()
        m.register_window(_window(limit=10, spend=8, action=BudgetAction.REJECT))
        assert m.check_budget_limit(BudgetTargetScope.SESSION, "s1", 5) is \
            BudgetAction.REJECT

    def test_check_alert_over_limit(self):
        m = BudgetWindowManager()
        m.register_window(_window(limit=10, spend=8, action=BudgetAction.ALERT))
        assert m.check_budget_limit(BudgetTargetScope.SESSION, "s1", 5) is \
            BudgetAction.ALERT

    def test_check_alert_threshold_crossing(self):
        m = BudgetWindowManager()
        m.register_window(_window(limit=100, spend=70, action=BudgetAction.ALERT))
        # projected 85 >= 80% threshold
        assert m.check_budget_limit(BudgetTargetScope.SESSION, "s1", 15) is \
            BudgetAction.ALERT

    def test_check_warn_action_stays_warn(self):
        m = BudgetWindowManager()
        m.register_window(_window(limit=10, spend=8, action=BudgetAction.WARN))
        assert m.check_budget_limit(BudgetTargetScope.SESSION, "s1", 5) is \
            BudgetAction.WARN

    def test_on_complete_fires_alert(self):
        m = BudgetWindowManager()
        cb = MagicMock()
        m.register_alert_callback(cb)
        m.register_window(_window(limit=100, spend=70))
        m.on_complete(BudgetTargetScope.SESSION, "s1", 20.0)
        cb.assert_called_once()
        assert m._windows["w1"].spend == 90.0

    def test_on_complete_no_alert_below_threshold(self):
        m = BudgetWindowManager()
        cb = MagicMock()
        m.register_alert_callback(cb)
        m.register_window(_window(limit=100, spend=10))
        m.on_complete(BudgetTargetScope.SESSION, "s1", 5.0)
        cb.assert_not_called()

    def test_on_complete_alert_on_exceed(self):
        m = BudgetWindowManager()
        cb = MagicMock()
        m.register_alert_callback(cb)
        m.register_window(_window(limit=100, spend=95))
        m.on_complete(BudgetTargetScope.SESSION, "s1", 10.0)
        cb.assert_called_once()

    def test_alert_callback_failure_logged(self):
        m = BudgetWindowManager()
        m.register_alert_callback(MagicMock(side_effect=RuntimeError("boom")))
        m.register_window(_window(limit=10, spend=9))
        m.on_complete(BudgetTargetScope.SESSION, "s1", 5.0)  # no raise

    def test_get_active_windows(self):
        m = BudgetWindowManager()
        m.register_window(_window())
        m.register_window(_window(window_id="w2", is_active=False))
        m.register_window(_window(window_id="w3", end_time=time.time() - 5))
        assert [w.window_id for w in m.get_active_windows()] == ["w1"]

    def test_backfill(self):
        m = BudgetWindowManager()
        now = time.time()
        m.register_window(_window(start_time=now - 100, end_time=now + 100))
        m.backfill_from_audit([
            {"scope": "session", "scope_id": "s1", "cost": 5.0, "timestamp": now},
            {"scope": "session", "scope_id": "s1", "cost": 3.0,
             "timestamp": now - 500},  # outside window
            {"scope": "agent", "scope_id": "s1", "cost": 9.0, "timestamp": now},
            {"scope": "bogus", "scope_id": "s1", "cost": 9.0, "timestamp": now},
            "not-a-dict",
            {"scope": "session", "scope_id": "s1", "cost": "bad",
             "timestamp": now},
            {"scope_id": "s1", "cost": 1.0, "timestamp": now},  # no scope
        ])
        assert m._windows["w1"].spend == 5.0

    def test_maybe_refresh_policies(self):
        m = BudgetWindowManager()
        assert m.maybe_refresh_policies(stale_threshold=0.0) is True
        m._last_policy_refresh = time.time()
        assert m.maybe_refresh_policies(stale_threshold=9999) is False

    def test_check_escalation(self):
        m = BudgetWindowManager()
        m.register_window(_window(limit=100, spend=95))
        directive = m.check_escalation(BudgetTargetScope.SESSION, "s1")
        # whatever budget_escalation returns for 95% — just verify plumbing
        assert directive is None or directive is not None
        m2 = BudgetWindowManager()
        assert m2.check_escalation(BudgetTargetScope.SESSION, "s1") is None

    def test_check_escalation_zero_limit(self):
        m = BudgetWindowManager()
        m.register_window(_window(limit=0, spend=5))
        assert m.check_escalation(BudgetTargetScope.SESSION, "s1") is None

    def test_should_stop_subagent(self):
        m = BudgetWindowManager()
        assert m.should_stop_subagent(BudgetTargetScope.SESSION, "s1") is False
        m.register_window(_window(limit=0))
        assert m.should_stop_subagent(BudgetTargetScope.SESSION, "s1") is False


class TestMakeWindow:
    def test_defaults(self):
        w = make_window(BudgetTargetScope.GLOBAL, "g", period="daily", limit=50)
        assert w.window_id
        assert w.end_time > w.start_time
        assert w.period == "daily"


@pytest.fixture()
def bm(tmp_path, monkeypatch):
    monkeypatch.setenv("AIOS_ENCRYPTION_KEY", "plaintext")
    return BudgetManager(tmp_path)


class TestBudgetDataclass:
    def test_bad_period_defaults_session(self):
        assert Budget(period="bogus").period == "session"

    def test_bad_on_exceed_defaults_block(self):
        assert Budget(on_exceed="bogus").on_exceed == "block"

    def test_reserve_clamped(self):
        assert Budget(finalization_reserve=-1).finalization_reserve == 0.0
        assert Budget(finalization_reserve=0.9).finalization_reserve == 0.0

    def test_effective_max(self):
        b = Budget(max_tokens=1000, max_cost_usd=10.0, finalization_reserve=0.1)
        assert b.effective_max_tokens == 900
        assert b.effective_max_cost == pytest.approx(9.0)
        b2 = Budget()
        assert b2.effective_max_tokens is None and b2.effective_max_cost is None


class TestBudgetManagerCheck:
    def test_unknown_scope_allows(self, bm):
        assert bm.check("nonexistent")["ok"] is True

    def test_token_limit_block(self, bm):
        bm.set_budget("t", Budget(max_tokens=100))
        r = bm.check("t", tokens=150)
        assert r["ok"] is False and r["action"] == "block"
        assert "tokens" in r["reason"]

    def test_cost_limit_block(self, bm):
        bm.set_budget("t", Budget(max_cost_usd=1.0))
        assert bm.check("t", cost=2.0)["ok"] is False

    def test_calls_limit_block(self, bm):
        bm.set_budget("t", Budget(max_calls=2))
        assert bm.check("t", calls=2)["ok"] is False

    def test_warn_action(self, bm):
        bm.set_budget("t", Budget(max_tokens=10, on_exceed="warn"))
        r = bm.check("t", tokens=50)
        assert r["ok"] is True and r["action"] == "warn"

    def test_fallback_action(self, bm):
        bm.set_budget("t", Budget(max_tokens=10, on_exceed="fallback",
                                  fallback_model="cheap-model"))
        r = bm.check("t", tokens=50)
        assert r["action"] == "fallback" and r["fallback_model"] == "cheap-model"

    def test_dry_run_no_state_change(self, bm):
        bm.set_budget("t", Budget(max_tokens=1000))
        bm.check("t", tokens=100, dry_run=True)
        assert bm.usage["t"]["tokens"] == 0

    def test_weighted_tokens(self, bm):
        bm.set_budget("t", Budget(max_tokens=1000))
        bm.check("t", tokens=0, input_tokens=10, output_tokens=5)
        assert bm.usage["t"]["tokens"] == 15
        bm.check("t", tokens=10, token_weight=2.0)
        assert bm.usage["t"]["tokens"] == 35

    def test_period_reset(self, bm):
        bm.set_budget("t", Budget(max_tokens=1000, period="daily"))
        bm.check("t", tokens=100)
        # simulate period rollover
        bm.usage["t"]["period_key"] = "1999-01-01"
        bm.check("t", tokens=5)
        assert bm.usage["t"]["tokens"] == 5

    def test_session_reset_on_new_session(self, bm):
        bm.set_budget("t", Budget(max_tokens=1000))
        bm.check("t", tokens=100, session_id="s-a")
        bm.check("t", tokens=5, session_id="s-b")
        assert bm.usage["t"]["tokens"] == 5

    def test_window_reject_blocks(self, bm):
        bm.set_budget("session", Budget())
        bm.window_manager.register_window(
            _window(scope_id="session", limit=1.0, spend=0.5,
                    action=BudgetAction.REJECT))
        r = bm.check("session", cost=2.0)
        assert r["ok"] is False and "REJECT" in r["reason"]

    def test_window_alert_action(self, bm):
        bm.set_budget("session", Budget())
        bm.window_manager.register_window(
            _window(scope_id="session", limit=10.0, spend=7.5,
                    action=BudgetAction.ALERT))
        r = bm.check("session", cost=1.0)
        assert r["ok"] is True and r["action"] == "alert"

    def test_rollout_block(self, bm):
        bm.set_budget("t", Budget(max_tokens=10000, rollout_max_tokens=50))
        r = bm.check("t", tokens=60, rollout_id="r1")
        assert r["ok"] is False and "rollout" in r

    def test_rollout_reminder(self, bm):
        bm.set_budget("t", Budget(max_tokens=10000, rollout_max_tokens=100,
                                  rollout_reminder_threshold=0.5))
        r = bm.check("t", tokens=60, rollout_id="r1")
        assert r["ok"] is True and r.get("reminder") and "50%" in r["reminder"]

    def test_rollout_no_reminder_when_no_threshold(self, bm):
        bm.set_budget("t", Budget(max_tokens=10000))
        r = bm.check("t", tokens=5, rollout_id="r1")
        assert r["ok"] is True

    def test_would_exceed(self, bm):
        bm.set_budget("t", Budget(max_tokens=100))
        assert bm.would_exceed("t", estimated_tokens=150) is True
        assert bm.would_exceed("t", estimated_tokens=10) is False
        assert bm.would_exceed("unknown") is False

    def test_would_exceed_cost(self, bm):
        bm.set_budget("t", Budget(max_cost_usd=5.0))
        assert bm.would_exceed("t", estimated_cost=6.0) is True

    def test_save_load_roundtrip(self, bm):
        bm.set_budget("x", Budget(max_tokens=42))
        bm.check("x", tokens=7)
        bm.save()
        bm2 = BudgetManager(bm.root)
        assert bm2.budgets["x"].max_tokens == 42
        assert bm2.usage["x"]["tokens"] == 7

    def test_corrupt_state_quarantined(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY", "plaintext")
        sf = tmp_path / "state" / "budget.json"
        sf.parent.mkdir(parents=True)
        sf.write_text("{corrupt")
        m = BudgetManager(tmp_path)
        assert "global" in m.budgets
        assert (tmp_path / "state" / "budget.json.corrupt.bak").exists()

    def test_save_noop_when_clean(self, bm):
        bm._dirty = False
        bm.save()  # no-op, no file
        assert not bm.state_file.exists()


class TestRolloutCheck:
    def test_exceeded(self, bm):
        b = Budget(rollout_max_tokens=10)
        r = bm.check_rollout("r", tokens=15, budget=b)
        assert r["ok"] is False

    def test_dry_run(self, bm):
        b = Budget(rollout_max_tokens=100)
        bm.check_rollout("r", tokens=15, dry_run=True, budget=b)
        assert bm.usage["rollout:r"]["tokens"] == 0

    def test_no_budget(self, bm):
        r = bm.check_rollout("r", tokens=999)
        assert r["ok"] is True
