
from runtime.budget import Budget, BudgetManager


def test_initial_budget(tmp_path):
    b = BudgetManager(tmp_path)
    assert "global" in b.budgets
    assert "session" in b.budgets


def test_block_on_exceed(tmp_path):
    b = BudgetManager(tmp_path)
    b.set_budget("session", Budget(max_tokens=10, on_exceed="block"))
    assert not b.check("session", tokens=20)["ok"]


def test_warn_on_exceed(tmp_path):
    b = BudgetManager(tmp_path)
    b.set_budget("session", Budget(max_tokens=5, on_exceed="warn"))
    assert b.check("session", tokens=10)["ok"]
    assert b.check("session", tokens=10)["action"] == "warn"


def test_persist_usage(tmp_path):
    b = BudgetManager(tmp_path)
    b.set_budget("session", Budget(max_tokens=100, on_exceed="block"))
    b.check("session", tokens=10)
    b.save()
    b2 = BudgetManager(tmp_path)
    assert b2.usage["session"]["tokens"] == 10
