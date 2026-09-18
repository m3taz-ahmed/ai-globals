"""Tests for runtime/budget_advanced.py — throttling, reserve/settle,
forecasting, anomaly detection, cost optimization, shadow mode."""

from __future__ import annotations

import pytest

from runtime.budget_advanced import (
    BurnForecaster,
    ModelCostOptimizer,
    ReserveSettleProtocol,
    ShadowModeTracker,
    SpendAnomalyDetector,
    ThrottleConfig,
    ThrottleTier,
    compute_throttle_tier,
)
from runtime.schemas import AizeeError


class TestThrottleTier:
    def test_below_advisory(self):
        assert compute_throttle_tier(50, 100) is None

    def test_advisory(self):
        assert compute_throttle_tier(60, 100) == ThrottleTier.ADVISORY

    def test_throttle(self):
        assert compute_throttle_tier(80, 100) == ThrottleTier.THROTTLE

    def test_restrict(self):
        assert compute_throttle_tier(95, 100) == ThrottleTier.RESTRICT

    def test_hard_stop(self):
        assert compute_throttle_tier(100, 100) == ThrottleTier.HARD_STOP
        assert compute_throttle_tier(150, 100) == ThrottleTier.HARD_STOP

    def test_zero_limit(self):
        assert compute_throttle_tier(10, 0) is None

    def test_custom_config(self):
        cfg = ThrottleConfig(advisory_pct=0.1, throttle_pct=0.2,
                           restrict_pct=0.3, hard_stop_pct=0.4)
        assert compute_throttle_tier(35, 100, cfg) == ThrottleTier.RESTRICT

    def test_config_unsorted_raises(self):
        with pytest.raises(ValueError, match="sorted"):
            ThrottleConfig(advisory_pct=0.9, throttle_pct=0.5)

    def test_config_out_of_range(self):
        with pytest.raises(ValueError, match="range"):
            ThrottleConfig(advisory_pct=-0.5)  # sorted, but out of [0,1]


class TestBurnForecaster:
    def test_window_validation(self):
        with pytest.raises(ValueError):
            BurnForecaster(window_seconds=0)

    def test_velocity_and_eta(self):
        f = BurnForecaster(window_seconds=60)
        for _ in range(10):
            f.record("s", 6.0)  # 60 total in 60s window -> 60/min
        fc = f.forecast("s", limit=600)
        assert fc.spend_velocity == pytest.approx(60.0)
        assert fc.eta_to_limit_seconds == pytest.approx((600 - 60) / 60 * 60)
        assert fc.confidence == pytest.approx(10 / 30)

    def test_no_events(self):
        f = BurnForecaster()
        fc = f.forecast("empty", limit=100)
        assert fc.spend_velocity == 0
        assert fc.eta_to_limit_seconds is None
        assert fc.will_breach is False
        assert fc.projected_end_spend == 0

    def test_breach_prediction(self):
        f = BurnForecaster(window_seconds=60)
        f.record("s", 700)  # velocity 700/min vs limit 600
        fc = f.forecast("s", limit=600)
        assert fc.will_breach is True
        assert fc.projected_end_spend >= 600

    def test_negative_amount_warns(self):
        f = BurnForecaster()
        f.record("s", -5)  # logs warning, still records
        fc = f.forecast("s", 100)
        assert fc.spend_velocity < 0

    def test_eviction(self):
        f = BurnForecaster(window_seconds=60)
        # Insert an event timestamped well outside the window directly.
        import time
        f._events["s"].append((time.time() - 120, 100.0))
        fc = f.forecast("s", 1000)
        assert fc.spend_velocity == 0  # old event evicted

    def test_scopes_isolated(self):
        f = BurnForecaster()
        f.record("a", 10)
        fc_b = f.forecast("b", 100)
        assert fc_b.projected_end_spend == 0


class TestSpendAnomalyDetector:
    def test_validation(self):
        with pytest.raises(ValueError):
            SpendAnomalyDetector(min_samples=1)
        with pytest.raises(ValueError):
            SpendAnomalyDetector(z_threshold=0)

    def test_insufficient_baseline(self):
        d = SpendAnomalyDetector(min_samples=3)
        r = d.check("s", 999.0)
        assert r.is_anomaly is False and r.z_score == 0.0

    def test_normal_spend(self):
        d = SpendAnomalyDetector(min_samples=5)
        for _ in range(5):
            d.record("s", 10.0)
        r = d.check("s", 10.5)
        assert r.is_anomaly is False

    def test_outlier_flagged(self):
        d = SpendAnomalyDetector(min_samples=5, z_threshold=2.0)
        for v in [10, 11, 9, 10, 11]:
            d.record("s", v)
        r = d.check("s", 100.0)
        assert r.is_anomaly is True
        assert r.z_score > 2.0
        assert r.baseline_mean == pytest.approx(10.2)

    def test_zero_variance(self):
        d = SpendAnomalyDetector(min_samples=3)
        for _ in range(3):
            d.record("s", 5.0)
        r = d.check("s", 5.0)
        assert r.is_anomaly is False and r.z_score == 0.0

    def test_check_adds_to_baseline(self):
        d = SpendAnomalyDetector(min_samples=3)
        d.check("s", 1.0)
        d.check("s", 2.0)
        d.check("s", 3.0)
        assert len(d._samples["s"]) == 3


class TestReserveSettle:
    def test_reserve_creates_hold(self):
        p = ReserveSettleProtocol()
        h = p.reserve("s", 0.5)
        assert h.amount == 0.5 and h.is_active
        assert h.to_dict()["hold_id"] == h.hold_id

    def test_reserve_negative(self):
        with pytest.raises(AizeeError):
            ReserveSettleProtocol().reserve("s", -1)

    def test_settle(self):
        p = ReserveSettleProtocol()
        h = p.reserve("s", 0.5)
        assert p.settle(h.hold_id, 0.42) is True
        assert h.settled and h.settled_amount == 0.42
        assert not h.is_active

    def test_settle_missing(self):
        assert ReserveSettleProtocol().settle("ghost", 1.0) is False

    def test_settle_twice(self):
        p = ReserveSettleProtocol()
        h = p.reserve("s", 0.5)
        p.settle(h.hold_id, 0.4)
        assert p.settle(h.hold_id, 0.4) is False

    def test_release(self):
        p = ReserveSettleProtocol()
        h = p.reserve("s", 0.5)
        assert p.release(h.hold_id) is True
        assert p.get_hold(h.hold_id) is None

    def test_release_missing(self):
        assert ReserveSettleProtocol().release("ghost") is False

    def test_release_settled(self):
        p = ReserveSettleProtocol()
        h = p.reserve("s", 0.5)
        p.settle(h.hold_id, 0.5)
        assert p.release(h.hold_id) is False

    def test_available_math(self):
        p = ReserveSettleProtocol()
        h1 = p.reserve("s", 0.3)
        p.reserve("s", 0.2)
        p.settle(h1.hold_id, 0.25)
        # limit 1.0 - settled 0.25 - reserved 0.2 = 0.55
        assert p.available("s", 1.0) == pytest.approx(0.55)

    def test_available_other_scope(self):
        p = ReserveSettleProtocol()
        p.reserve("a", 0.9)
        assert p.available("b", 1.0) == 1.0

    def test_available_floor_zero(self):
        p = ReserveSettleProtocol()
        p.reserve("s", 5.0)
        assert p.available("s", 1.0) == 0.0

    def test_expired_hold_purged(self):
        p = ReserveSettleProtocol()
        h = p.reserve("s", 0.5, ttl_seconds=-1)  # already expired
        assert h.is_expired and not h.is_active
        assert p.available("s", 1.0) == 1.0  # purged on access

    def test_settle_expired(self):
        p = ReserveSettleProtocol()
        h = p.reserve("s", 0.5, ttl_seconds=-1)
        assert p.settle(h.hold_id, 0.4) is False


class TestModelCostOptimizer:
    def test_unknown_model(self):
        with pytest.raises(AizeeError):
            ModelCostOptimizer().compare("no-such-model")

    def test_compare_sorted(self):
        r = ModelCostOptimizer().compare("gpt-4o")
        costs = [x["cost_per_call"] for x in r]
        assert costs == sorted(costs)
        assert len(r) == len(ModelCostOptimizer.PRICING)
        # gpt-4o itself has 0% savings vs itself
        self_row = next(x for x in r if x["model"] == "gpt-4o")
        assert self_row["savings_pct"] == 0.0
        assert self_row["capability_tier"] == "high"

    def test_recommend_cheaper_medium(self):
        r = ModelCostOptimizer().recommend("gpt-4o", capability_tier="medium")
        assert r["cost_per_call"] < ModelCostOptimizer()._cost_per_call("gpt-4o")
        assert r["capability_tier"] in ("medium", "high")

    def test_recommend_respects_tier(self):
        opt = ModelCostOptimizer()
        r = opt.recommend("gpt-4o", capability_tier="high")
        # cheapest high-tier model
        assert r["capability_tier"] == "high"

    def test_recommend_no_alternative(self):
        # cheapest model overall is gemini-1.5-flash-8b (low tier)
        r = ModelCostOptimizer().recommend("gemini-1.5-flash-8b", capability_tier="low")
        assert r["model"] == "gemini-1.5-flash-8b"
        assert "note" in r

    def test_recommend_unknown_tier_defaults(self):
        r = ModelCostOptimizer().recommend("gpt-4o", capability_tier="bogus")
        assert "model" in r  # treated as medium

    def test_savings_projection(self):
        r = ModelCostOptimizer().savings_projection("gpt-4o", "gpt-4o-mini", 10000)
        assert r["monthly_savings"] > 0
        assert r["current_monthly_cost"] > r["recommended_monthly_cost"]
        assert r["savings_pct"] > 0

    def test_cost_per_call_math(self):
        opt = ModelCostOptimizer()
        cost = opt._cost_per_call("gpt-4o", input_tokens=1_000_000, output_tokens=1_000_000)
        assert cost == pytest.approx(2.50 + 10.00)


class TestShadowMode:
    def test_record_and_report(self):
        t = ShadowModeTracker()
        t.record("s1", "llm_call", True, "throttle tier")
        t.record("s1", "llm_call", False, "ok")
        t.record("s2", "llm_call", True, "restrict")
        rep = t.report()
        assert rep["total_evaluations"] == 3
        assert rep["total_would_trip"] == 2
        assert rep["overall_trip_rate_pct"] == pytest.approx(66.67)
        assert rep["per_scope"]["s1"]["would_trip_count"] == 1
        assert len(rep["recent_trips"]) == 2

    def test_empty_report(self):
        rep = ShadowModeTracker().report()
        assert rep["total_evaluations"] == 0
        assert rep["overall_trip_rate_pct"] == 0.0

    def test_reset(self):
        t = ShadowModeTracker()
        t.record("s", "a", True, "r")
        t.reset()
        assert t.report()["total_evaluations"] == 0
