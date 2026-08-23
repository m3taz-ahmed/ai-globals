"""Tests for eval.reliability — reliability@k and security-adjusted scoring."""

from __future__ import annotations

import math

import pytest

from eval.reliability import (
    ReliabilityEvaluator,
    ReliabilityScore,
    Rollout,
    RolloutStatus,
    reliability_at_k,
    security_adjusted_reliability,
)


# ---------------------------------------------------------------------------
# reliability_at_k
# ---------------------------------------------------------------------------

def test_reliability_at_k_zero_rollouts_returns_zero() -> None:
    # Arrange / Act
    result = reliability_at_k(n=0, c=0, k=1)
    # Assert
    assert result == 0.0


def test_reliability_at_k_all_pass_returns_one() -> None:
    # Arrange / Act
    result = reliability_at_k(n=10, c=10, k=1)
    # Assert
    assert result == 1.0


def test_reliability_at_k_none_pass_returns_zero() -> None:
    # Arrange / Act
    result = reliability_at_k(n=10, c=0, k=1)
    # Assert
    assert result == 0.0


def test_reliability_at_k_half_pass_k1_is_empirical_rate() -> None:
    # Arrange / Act
    result = reliability_at_k(n=10, c=5, k=1)
    # Assert
    assert result == 0.5


def test_reliability_at_k_half_pass_k5_uses_comb_formula() -> None:
    # Arrange
    n, c, k = 10, 5, 5
    expected = 1.0 - math.comb(n - c, k) / math.comb(n, k)
    # Act
    result = reliability_at_k(n=n, c=c, k=k)
    # Assert
    assert result == expected


def test_reliability_at_k_n_less_than_k_falls_back_to_rate() -> None:
    # Arrange: n=3, c=2, k=5 -> cannot sample 5 from 3, fall back to c/n
    # Act
    result = reliability_at_k(n=3, c=2, k=5)
    # Assert
    assert result == 2 / 3


def test_reliability_at_k_clamps_to_unit_interval() -> None:
    # Arrange / Act: a degenerate input that would exceed [0,1] is clamped.
    # n<k path with c>n is impossible in practice, but clamp must hold.
    result = reliability_at_k(n=2, c=5, k=5)
    # Assert
    assert 0.0 <= result <= 1.0


# ---------------------------------------------------------------------------
# security_adjusted_reliability
# ---------------------------------------------------------------------------

def test_security_adjusted_reliability_uses_secure_count() -> None:
    # Arrange / Act
    result = security_adjusted_reliability(n=10, c_secure=3, k=1)
    # Assert
    assert result == pytest.approx(0.3)


# ---------------------------------------------------------------------------
# Rollout dataclass + RolloutStatus enum
# ---------------------------------------------------------------------------

def test_rollout_status_enum_values() -> None:
    # Arrange / Act / Assert
    assert RolloutStatus.PASS.value == "pass"
    assert RolloutStatus.FAIL.value == "fail"
    assert RolloutStatus.SECURITY_FAIL.value == "security_fail"


def test_rollout_dataclass_defaults() -> None:
    # Arrange / Act
    rollout = Rollout(task_id="t1", rollout_id=0, status=RolloutStatus.PASS)
    # Assert
    assert rollout.task_id == "t1"
    assert rollout.rollout_id == 0
    assert rollout.status is RolloutStatus.PASS
    assert rollout.tokens == 0
    assert rollout.duration_s == 0.0


# ---------------------------------------------------------------------------
# ReliabilityEvaluator
# ---------------------------------------------------------------------------

def test_evaluator_add_rollout_and_score() -> None:
    # Arrange
    ev = ReliabilityEvaluator()
    ev.add_rollout(Rollout("t1", 0, RolloutStatus.PASS))
    ev.add_rollout(Rollout("t1", 1, RolloutStatus.FAIL))
    # Act
    score = ev.score("t1", k=1)
    # Assert
    assert score.task_id == "t1"
    assert score.k == 1
    assert score.n == 2
    assert score.c == 1
    assert score.reliability == 0.5
    assert score.security_adjusted == 0.5
    assert score.pass_at_k == score.reliability


def test_evaluator_add_rollouts_batch() -> None:
    # Arrange
    ev = ReliabilityEvaluator()
    rollouts = [
        Rollout("t1", 0, RolloutStatus.PASS),
        Rollout("t1", 1, RolloutStatus.PASS),
        Rollout("t1", 2, RolloutStatus.FAIL),
    ]
    # Act
    ev.add_rollouts(rollouts)
    score = ev.score("t1", k=1)
    # Assert
    assert score.n == 3
    assert score.c == 2
    assert score.reliability == pytest.approx(2 / 3)


def test_evaluator_score_all_covers_every_task() -> None:
    # Arrange
    ev = ReliabilityEvaluator()
    ev.add_rollout(Rollout("t1", 0, RolloutStatus.PASS))
    ev.add_rollout(Rollout("t1", 1, RolloutStatus.FAIL))
    ev.add_rollout(Rollout("t2", 0, RolloutStatus.PASS))
    # Act
    scores = ev.score_all(k=1)
    # Assert
    assert len(scores) == 2
    by_task = {s.task_id: s for s in scores}
    assert by_task["t1"].n == 2
    assert by_task["t2"].n == 1
    assert by_task["t2"].reliability == 1.0


def test_evaluator_summary_returns_means() -> None:
    # Arrange
    ev = ReliabilityEvaluator()
    ev.add_rollout(Rollout("t1", 0, RolloutStatus.PASS))
    ev.add_rollout(Rollout("t1", 1, RolloutStatus.FAIL))
    ev.add_rollout(Rollout("t2", 0, RolloutStatus.PASS))
    # Act
    summary = ev.summary(k=1)
    # Assert: t1 reliability 0.5, t2 reliability 1.0 -> mean 0.75
    assert summary["mean_reliability"] == 0.75
    assert summary["mean_security_adjusted"] == 0.75
    assert summary["total_tasks"] == 2.0
    assert summary["total_rollouts"] == 3.0


def test_evaluator_summary_empty_returns_zeros() -> None:
    # Arrange
    ev = ReliabilityEvaluator()
    # Act
    summary = ev.summary(k=1)
    # Assert
    assert summary["mean_reliability"] == 0.0
    assert summary["mean_security_adjusted"] == 0.0
    assert summary["total_tasks"] == 0.0
    assert summary["total_rollouts"] == 0.0


def test_evaluator_clear_removes_all_rollouts() -> None:
    # Arrange
    ev = ReliabilityEvaluator()
    ev.add_rollout(Rollout("t1", 0, RolloutStatus.PASS))
    # Act
    ev.clear()
    score = ev.score("t1", k=1)
    # Assert
    assert score.n == 0
    assert score.reliability == 0.0


# ---------------------------------------------------------------------------
# Mixed PASS / FAIL / SECURITY_FAIL
# ---------------------------------------------------------------------------

def test_evaluator_mixed_statuses_c_excludes_security_fail() -> None:
    # Arrange: 1 PASS, 1 FAIL, 1 SECURITY_FAIL
    ev = ReliabilityEvaluator()
    ev.add_rollouts([
        Rollout("t1", 0, RolloutStatus.PASS),
        Rollout("t1", 1, RolloutStatus.FAIL),
        Rollout("t1", 2, RolloutStatus.SECURITY_FAIL),
    ])
    # Act
    score = ev.score("t1", k=1)
    # Assert: only PASS counts toward c and c_secure
    assert score.n == 3
    assert score.c == 1
    assert score.security_adjusted == pytest.approx(1 / 3)
    assert score.reliability == pytest.approx(1 / 3)


# ---------------------------------------------------------------------------
# ReliabilityScore.to_dict
# ---------------------------------------------------------------------------

def test_reliability_score_to_dict_roundtrip() -> None:
    # Arrange
    score = ReliabilityScore(
        task_id="t1",
        k=2,
        n=10,
        c=5,
        reliability=0.9,
        security_adjusted=0.4,
        pass_at_k=0.9,
    )
    # Act
    d = score.to_dict()
    # Assert
    assert d == {
        "task_id": "t1",
        "k": 2,
        "n": 10,
        "c": 5,
        "reliability": 0.9,
        "security_adjusted": 0.4,
        "pass_at_k": 0.9,
    }
