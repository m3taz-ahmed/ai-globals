"""Gap coverage for eval/reliability.py."""

from __future__ import annotations

import pytest

from eval.reliability import (
    DimensionScores,
    ReliabilityError,
    ReliabilityEvaluator,
    Rollout,
    RolloutStatus,
    Verdict,
    _clamp01,
    compute_task_score,
    k_needed_estimate,
    pass_at_k,
    pass_cubed,
    pass_hat_k,
    priority_ladder,
    reliability_at_k,
    security_adjusted_reliability,
    wilson_ci,
)


class TestReliabilityError:
    def test_carries_context(self):
        err = ReliabilityError("boom", {"k": 3})
        assert "boom" in str(err)


class TestReliabilityAtK:
    def test_zero_n(self):
        assert reliability_at_k(0, 0, 1) == 0.0

    def test_n_less_than_k_uses_rate(self):
        assert reliability_at_k(2, 1, 5) == pytest.approx(0.5)

    def test_zero_passes(self):
        assert reliability_at_k(5, 0, 1) == 0.0

    def test_all_pass(self):
        assert reliability_at_k(5, 5, 2) == 1.0

    def test_math_path(self):
        # n=4, c=2, k=2 -> 1 - C(2,2)/C(4,2) = 1 - 1/6
        assert reliability_at_k(4, 2, 2) == pytest.approx(1.0 - 1 / 6)

    def test_security_adjusted_matches(self):
        assert security_adjusted_reliability(4, 2, 2) == reliability_at_k(4, 2, 2)

    def test_clamp01_bounds(self):
        assert _clamp01(-0.5) == 0.0
        assert _clamp01(1.5) == 1.0
        assert _clamp01(0.4) == 0.4


class TestReliabilityEvaluator:
    def test_full_lifecycle(self):
        ev = ReliabilityEvaluator()
        ev.add_rollout(Rollout("t1", 0, RolloutStatus.PASS))
        ev.add_rollouts([
            Rollout("t1", 1, RolloutStatus.FAIL),
            Rollout("t1", 2, RolloutStatus.SECURITY_FAIL),
            Rollout("t2", 0, RolloutStatus.PASS),
            Rollout("t1", 3, RolloutStatus.PASS),
        ])
        s = ev.score("t1", k=1)
        assert s.n == 4
        assert s.c == 2
        d = s.to_dict()
        assert d["task_id"] == "t1" and d["k"] == 1

        all_scores = ev.score_all(k=1)
        assert [x.task_id for x in all_scores] == ["t1", "t2"]

        summary = ev.summary(k=1)
        assert summary["total_tasks"] == 2.0
        assert summary["total_rollouts"] == 5.0

        ev.clear()
        assert ev.score_all() == []

    def test_summary_empty(self):
        ev = ReliabilityEvaluator()
        summary = ev.summary()
        assert summary["mean_reliability"] == 0.0
        assert summary["total_tasks"] == 0.0


class TestWilsonAndEstimate:
    def test_wilson_zero_n(self):
        with pytest.raises(ValueError):
            wilson_ci(0, 0)

    def test_wilson_bounds(self):
        lo, hi = wilson_ci(8, 10)
        assert 0.0 <= lo < hi <= 1.0

    def test_k_needed_zero_k(self):
        assert k_needed_estimate(5, 0, 0.5, 10) is None

    def test_k_needed_unreachable(self):
        assert k_needed_estimate(5, 10, 0.9, 10) is None

    def test_k_needed_success(self):
        n = k_needed_estimate(9, 10, 0.5, 10)
        assert n is not None and n > 10

    def test_k_needed_cap_exceeded(self):
        assert k_needed_estimate(9, 10, 0.95, 10) is None


class TestPassMetrics:
    def test_pass_at_k_empty(self):
        assert pass_at_k([], 1) == 0.0
        assert pass_at_k([1.0], 5) == 0.0

    def test_pass_at_k_math(self):
        assert pass_at_k([0.9, 0.1, 0.8, 0.2], k=2) == pytest.approx(
            1.0 - 1 / 6
        )

    def test_pass_hat_k(self):
        assert pass_hat_k([], 1) == 0.0
        assert pass_hat_k([0.9, 0.1], k=2) == pytest.approx(0.25)

    def test_pass_cubed(self):
        assert pass_cubed([1, 0, 1, 1, 0, 1, 1, 1, 0, 1]) == pass_at_k(
            [1, 0, 1, 1, 0, 1, 1, 1, 0, 1], k=3
        )

    def test_compute_task_score_veto(self):
        base = DimensionScores(1.0, 1.0, 1.0)
        assert compute_task_score(base) == pytest.approx(1.0)
        vetoed = DimensionScores(1.0, 1.0, 0.0)
        assert compute_task_score(vetoed) == 0.0


class TestPriorityLadder:
    def test_env_unstable(self):
        a = priority_ladder(10, 9, env_stable=False)
        assert a.verdict is Verdict.INSUFFICIENT
        assert "ENV_UNSTABLE" in a.reason_codes

    def test_audit_integrity(self):
        a = priority_ladder(10, 9, audit_integrity=False)
        assert a.verdict is Verdict.KILL
        assert "AUDIT_INTEGRITY" in a.reason_codes

    def test_low_power(self):
        a = priority_ladder(3, 3, k_min=5)
        assert a.verdict is Verdict.INSUFFICIENT
        assert "LOW_POWER" in a.reason_codes

    def test_critical_event_safety_task(self):
        a = priority_ladder(10, 9, has_critical_event=True, safety_critical=True)
        assert a.verdict is Verdict.KILL
        assert "CRITICAL_EVENT" in a.reason_codes

    def test_reliability_refuted(self):
        # 0/10 passes -> wilson hi far below target
        a = priority_ladder(10, 0, target=0.8)
        assert a.verdict is Verdict.KILL
        assert "RELIABILITY_REFUTED" in a.reason_codes

    def test_reliability_confirmed(self):
        a = priority_ladder(50, 49, target=0.8)
        assert a.verdict is Verdict.PASS
        assert a.reason_codes == []
        assert a.to_dict()["verdict"] == "pass"

    def test_ci_straddles(self):
        # ~55% pass rate straddles a 0.5 target
        a = priority_ladder(10, 6, target=0.55)
        assert a.verdict is Verdict.INSUFFICIENT
        assert "CI_STRADDLES_THRESHOLD" in a.reason_codes

    def test_critical_event_non_safety_straddles(self):
        # high pass rate + critical event but NOT safety-critical:
        # lo >= target but has_critical_event -> falls through to straddle
        a = priority_ladder(50, 49, target=0.8, has_critical_event=True)
        assert a.verdict is Verdict.INSUFFICIENT
