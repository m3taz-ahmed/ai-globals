"""Tests for budget finalization reserve and would_exceed (from AgentBudget)."""

from __future__ import annotations

from pathlib import Path

from runtime.budget import Budget, BudgetManager


def test_finalization_reserve_default_zero() -> None:
    b = Budget(max_tokens=1000)
    assert b.finalization_reserve == 0.0
    assert b.effective_max_tokens == 1000


def test_finalization_reserve_reduces_effective_max() -> None:
    b = Budget(max_tokens=1000, finalization_reserve=0.05)
    assert b.finalization_reserve == 0.05
    assert b.effective_max_tokens == 950  # 1000 * 0.95


def test_finalization_reserve_cost() -> None:
    b = Budget(max_cost_usd=10.0, finalization_reserve=0.10)
    assert b.effective_max_cost == 9.0  # 10 * 0.90


def test_finalization_reserve_clamped() -> None:
    b = Budget(max_tokens=1000, finalization_reserve=0.6)  # > 0.5, clamped to 0
    assert b.finalization_reserve == 0.0


def test_finalization_reserve_negative_clamped() -> None:
    b = Budget(max_tokens=1000, finalization_reserve=-0.1)
    assert b.finalization_reserve == 0.0


def test_would_exceed_false_when_under_budget(tmp_path: Path) -> None:
    mgr = BudgetManager(tmp_path)
    mgr.set_budget("session", Budget(max_tokens=1000, max_cost_usd=10.0))
    assert mgr.would_exceed("session", estimated_cost=1.0, estimated_tokens=100) is False


def test_would_exceed_true_when_over_effective_max(tmp_path: Path) -> None:
    mgr = BudgetManager(tmp_path)
    mgr.set_budget("session", Budget(max_tokens=1000, max_cost_usd=10.0, finalization_reserve=0.10))
    # effective_max_tokens = 900, effective_max_cost = 9.0
    # First, consume most of the budget
    mgr.check("session", tokens=850, cost=8.5)
    # Now check if adding more would exceed
    assert mgr.would_exceed("session", estimated_cost=1.0, estimated_tokens=100) is True


def test_would_exceed_false_when_no_budget(tmp_path: Path) -> None:
    mgr = BudgetManager(tmp_path)
    # "nonexistent" scope has no budget
    assert mgr.would_exceed("nonexistent", estimated_cost=1000) is False
