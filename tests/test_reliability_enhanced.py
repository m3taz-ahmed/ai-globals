"""Tests for eval.reliability enhancements — Wilson, Pass^3, priority ladder, weighted scoring."""

from __future__ import annotations

import pytest

from eval.reliability import (
    DimensionScores,
    Verdict,
    compute_task_score,
    k_needed_estimate,
    pass_at_k,
    pass_cubed,
    pass_hat_k,
    priority_ladder,
    wilson_ci,
)

# -- Wilson CI ----------------------------------------------------------------

def test_wilson_ci_all_successes() -> None:
    lo, hi = wilson_ci(10, 10)
    assert lo > 0.5
    assert hi <= 1.0


def test_wilson_ci_all_failures() -> None:
    lo, hi = wilson_ci(0, 10)
    assert lo == 0.0
    assert hi < 0.5


def test_wilson_ci_half_success() -> None:
    lo, hi = wilson_ci(5, 10)
    assert 0.1 < lo < 0.5
    assert 0.5 < hi < 0.9


def test_wilson_ci_raises_on_zero_n() -> None:
    with pytest.raises(ValueError):
        wilson_ci(0, 0)


def test_wilson_ci_bounds_in_unit_interval() -> None:
    for s in range(11):
        lo, hi = wilson_ci(s, 10)
        assert 0.0 <= lo <= 1.0
        assert 0.0 <= hi <= 1.0
        assert lo <= hi


# -- k_needed_estimate --------------------------------------------------------

def test_k_needed_unreachable_returns_none() -> None:
    # p_hat = 0.5, target = 0.8 → unreachable
    assert k_needed_estimate(5, 10, r=0.8, k_planned=10) is None


def test_k_needed_reachable() -> None:
    # p_hat = 0.9, target = 0.8 → should find a value
    result = k_needed_estimate(9, 10, r=0.8, k_planned=10)
    assert result is not None
    assert result > 10


def test_k_needed_respects_cap() -> None:
    # p_hat barely above target, cap should kick in
    result = k_needed_estimate(6, 10, r=0.5, k_planned=5, cap_multiplier=2)
    # With cap=10, should find quickly or hit cap
    assert result is None or result <= 10


# -- pass_at_k / pass_hat_k / pass_cubed --------------------------------------

def test_pass_at_k_all_pass() -> None:
    scores = [1.0] * 10
    assert pass_at_k(scores, k=1) == 1.0
    assert pass_at_k(scores, k=3) == 1.0


def test_pass_at_k_all_fail() -> None:
    scores = [0.0] * 10
    assert pass_at_k(scores, k=1) == 0.0


def test_pass_at_k_empty() -> None:
    assert pass_at_k([], k=1) == 0.0


def test_pass_hat_k_simple() -> None:
    scores = [1.0, 0.0, 1.0, 1.0, 0.0]
    # 3/5 pass, pass^1 = 0.6
    assert abs(pass_hat_k(scores, k=1) - 0.6) < 0.001
    # pass^2 = 0.36
    assert abs(pass_hat_k(scores, k=2) - 0.36) < 0.001


def test_pass_cubed_requires_three() -> None:
    scores = [1.0, 0.0, 1.0, 1.0, 0.0, 1.0, 1.0, 1.0, 0.0, 1.0]
    result = pass_cubed(scores)
    assert 0.0 < result < 1.0


# -- compute_task_score -------------------------------------------------------

def test_task_score_safety_veto() -> None:
    # safety=0 → entire score is 0 regardless of completion
    scores = DimensionScores(completion=1.0, robustness=1.0, safety=0.0)
    assert compute_task_score(scores) == 0.0


def test_task_score_full_pass() -> None:
    scores = DimensionScores(completion=1.0, robustness=1.0, safety=1.0)
    assert compute_task_score(scores) == 1.0


def test_task_score_weighted() -> None:
    # base = 0.8*0.8 + 0.2*0.6 = 0.76, safety=1.0 → 0.76
    scores = DimensionScores(completion=0.8, robustness=0.6, safety=1.0)
    assert compute_task_score(scores) == 0.76


# -- priority_ladder ----------------------------------------------------------

def test_priority_ladder_env_unstable() -> None:
    result = priority_ladder(n=10, c=10, env_stable=False)
    assert result.verdict is Verdict.INSUFFICIENT
    assert "ENV_UNSTABLE" in result.reason_codes


def test_priority_ladder_audit_integrity() -> None:
    result = priority_ladder(n=10, c=10, audit_integrity=False)
    assert result.verdict is Verdict.KILL
    assert "AUDIT_INTEGRITY" in result.reason_codes


def test_priority_ladder_low_power() -> None:
    result = priority_ladder(n=3, c=3, k_min=5)
    assert result.verdict is Verdict.INSUFFICIENT
    assert "LOW_POWER" in result.reason_codes


def test_priority_ladder_critical_event() -> None:
    result = priority_ladder(n=10, c=10, has_critical_event=True, safety_critical=True)
    assert result.verdict is Verdict.KILL
    assert "CRITICAL_EVENT" in result.reason_codes


def test_priority_ladder_refuted() -> None:
    # 3/10 pass → Wilson upper bound will be below 0.8
    result = priority_ladder(n=10, c=3, target=0.8)
    assert result.verdict is Verdict.KILL
    assert "RELIABILITY_REFUTED" in result.reason_codes


def test_priority_ladder_confirmed() -> None:
    # 30/30 pass → Wilson lower bound will be above 0.8
    result = priority_ladder(n=30, c=30, target=0.8)
    assert result.verdict is Verdict.PASS
    assert result.reason_codes == []


def test_priority_ladder_straddles() -> None:
    # 8/10 pass → Wilson CI likely straddles 0.8
    result = priority_ladder(n=10, c=8, target=0.8)
    # Could be PASS or INSUFFICIENT depending on Wilson bounds
    assert result.verdict in (Verdict.PASS, Verdict.INSUFFICIENT)


def test_task_audit_to_dict() -> None:
    result = priority_ladder(n=10, c=10, target=0.8)
    d = result.to_dict()
    assert "verdict" in d
    assert "reason_codes" in d
    assert "n" in d
    assert "c" in d
