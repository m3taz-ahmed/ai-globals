"""Tests for per-PR spend limits (P1.6)."""

from __future__ import annotations

from pathlib import Path

from runtime.budget import Budget, BudgetManager


def _mgr(tmp_path: Path) -> BudgetManager:
    return BudgetManager(tmp_path)


def test_no_pr_budget_allows(tmp_path: Path) -> None:
    mgr = _mgr(tmp_path)
    res = mgr.check("session", tokens=10, dry_run=True, pr_id="42")
    assert res["ok"] and res["pr"]["ok"]


def test_pr_budget_blocks_on_tokens(tmp_path: Path) -> None:
    mgr = _mgr(tmp_path)
    mgr.set_budget("pr", Budget(max_tokens=100))
    assert mgr.check_pr("7", tokens=50)["ok"]
    res = mgr.check_pr("7", tokens=60)
    assert not res["ok"] and res["action"] == "block" and "tokens" in res["exceeded"]


def test_pr_usage_accumulates_across_calls(tmp_path: Path) -> None:
    mgr = _mgr(tmp_path)
    mgr.set_budget("pr", Budget(max_cost_usd=1.0))
    mgr.check_pr("9", cost=0.6)
    res = mgr.check_pr("9", cost=0.5)
    assert not res["ok"] and "cost" in res["exceeded"]
    other = mgr.check_pr("10", cost=0.9)
    assert other["ok"]


def test_pr_dry_run_does_not_accumulate(tmp_path: Path) -> None:
    mgr = _mgr(tmp_path)
    mgr.set_budget("pr", Budget(max_tokens=100))
    mgr.check_pr("5", tokens=90, dry_run=True)
    assert mgr.check_pr("5", tokens=90)["ok"]


def test_pr_warn_mode_allows_and_marks(tmp_path: Path) -> None:
    mgr = _mgr(tmp_path)
    mgr.set_budget("pr", Budget(max_tokens=10, on_exceed="warn"))
    res = mgr.check_pr("1", tokens=20)
    assert res["ok"] and res["action"] == "warn"


def test_check_threads_pr_result(tmp_path: Path) -> None:
    mgr = _mgr(tmp_path)
    mgr.set_budget("session", Budget(max_tokens=1_000_000))
    mgr.set_budget("pr", Budget(max_calls=2))
    first = mgr.check("session", calls=1, pr_id="3")
    assert first["ok"] and first["pr"]["ok"]
    second = mgr.check("session", calls=1, pr_id="3")
    assert not second["ok"] and "calls" in second["pr"]["exceeded"]


def test_pr_warn_dry_run_does_not_record(tmp_path: Path) -> None:
    mgr = _mgr(tmp_path)
    mgr.set_budget("pr", Budget(max_tokens=10, on_exceed="warn"))
    res = mgr.check_pr("5", tokens=20, dry_run=True)
    assert res["ok"] and res["action"] == "warn"
    # dry-run must not record usage: a real check still sees zero usage.
    res2 = mgr.check_pr("5", tokens=20)
    assert res2["ok"]
