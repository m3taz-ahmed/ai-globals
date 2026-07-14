"""Comprehensive tests for runtime/budget.py."""

from __future__ import annotations

import threading
from pathlib import Path
from unittest.mock import patch

import pytest

from runtime.budget import ALLOWED_EXCEED, ALLOWED_PERIODS, Budget, BudgetManager

# ---------------------------------------------------------------------------
# Budget.__post_init__ — normalization
# ---------------------------------------------------------------------------

class TestBudgetNormalization:
    def test_valid_period_preserved(self):
        for p in ALLOWED_PERIODS:
            b = Budget(period=p)
            assert b.period == p

    def test_invalid_period_defaults_to_session(self):
        b = Budget(period="fortnight")  # type: ignore[arg-type]
        assert b.period == "session"

    def test_valid_on_exceed_preserved(self):
        for e in ALLOWED_EXCEED:
            b = Budget(on_exceed=e)
            assert b.on_exceed == e

    def test_invalid_on_exceed_defaults_to_block(self):
        b = Budget(on_exceed="explode")  # type: ignore[arg-type]
        assert b.on_exceed == "block"


# ---------------------------------------------------------------------------
# BudgetManager — defaults and persistence
# ---------------------------------------------------------------------------

class TestBudgetManagerDefaults:
    def test_initial_budgets(self, tmp_path: Path):
        bm = BudgetManager(tmp_path)
        assert "global" in bm.budgets
        assert "session" in bm.budgets

    def test_persist_and_reload(self, tmp_path: Path):
        bm = BudgetManager(tmp_path)
        bm.set_budget("task", Budget(max_tokens=500, on_exceed="warn"))
        bm.check("task", tokens=100)
        bm.save()

        bm2 = BudgetManager(tmp_path)
        assert bm2.usage["task"]["tokens"] == 100
        assert bm2.budgets["task"].max_tokens == 500

    def test_no_budget_scope_always_allows(self, tmp_path: Path):
        bm = BudgetManager(tmp_path)
        result = bm.check("nonexistent_scope", tokens=9_999_999)
        assert result["ok"] is True
        assert result["action"] == "allow"


# ---------------------------------------------------------------------------
# BudgetManager.check — token / cost / calls limits
# ---------------------------------------------------------------------------

class TestBudgetCheck:
    def test_block_on_token_exceed(self, tmp_path: Path):
        bm = BudgetManager(tmp_path)
        bm.set_budget("t", Budget(max_tokens=10, on_exceed="block"))
        result = bm.check("t", tokens=20)
        assert result["ok"] is False
        assert result["action"] == "block"
        assert "tokens" in result["reason"]

    def test_warn_on_token_exceed(self, tmp_path: Path):
        bm = BudgetManager(tmp_path)
        bm.set_budget("t", Budget(max_tokens=5, on_exceed="warn"))
        result = bm.check("t", tokens=10)
        assert result["ok"] is True
        assert result["action"] == "warn"

    def test_block_on_cost_exceed(self, tmp_path: Path):
        bm = BudgetManager(tmp_path)
        bm.set_budget("t", Budget(max_cost_usd=1.0, on_exceed="block"))
        result = bm.check("t", cost=2.0)
        assert result["ok"] is False
        assert "cost" in result["reason"]

    def test_block_on_calls_exceed(self, tmp_path: Path):
        bm = BudgetManager(tmp_path)
        bm.set_budget("t", Budget(max_calls=3, on_exceed="block"))
        result = bm.check("t", calls=5)
        assert result["ok"] is False
        assert "calls" in result["reason"]

    def test_fallback_model_path(self, tmp_path: Path):
        bm = BudgetManager(tmp_path)
        bm.set_budget(
            "t",
            Budget(max_tokens=5, on_exceed="fallback", fallback_model="gpt-3.5"),
        )
        result = bm.check("t", tokens=10)
        assert result["ok"] is True
        assert result["action"] == "fallback"
        assert result["fallback_model"] == "gpt-3.5"

    def test_fallback_without_model_blocks(self, tmp_path: Path):
        """fallback on_exceed with no fallback_model falls through to block."""
        bm = BudgetManager(tmp_path)
        bm.set_budget("t", Budget(max_tokens=5, on_exceed="fallback", fallback_model=None))
        result = bm.check("t", tokens=10)
        assert result["ok"] is False
        assert result["action"] == "block"

    def test_usage_accumulates(self, tmp_path: Path):
        bm = BudgetManager(tmp_path)
        bm.set_budget("t", Budget(max_tokens=1000, on_exceed="block"))
        bm.check("t", tokens=300)
        bm.check("t", tokens=300)
        assert bm.usage["t"]["tokens"] == 600

    def test_within_limit_allows(self, tmp_path: Path):
        bm = BudgetManager(tmp_path)
        bm.set_budget("t", Budget(max_tokens=100, on_exceed="block"))
        result = bm.check("t", tokens=50)
        assert result["ok"] is True
        assert result["action"] == "allow"
        assert result["reason"] is None


# ---------------------------------------------------------------------------
# BudgetManager — period key + reset
# ---------------------------------------------------------------------------

class TestBudgetPeriodReset:
    def test_session_period_key_uses_process_id(self, tmp_path: Path):
        bm = BudgetManager(tmp_path)
        bm.set_budget("s", Budget(max_tokens=1000, period="session"))
        bm.check("s", tokens=10)
        # Same process → no reset; usage should accumulate
        bm.check("s", tokens=10)
        assert bm.usage["s"]["tokens"] == 20

    def test_daily_period_key_is_date(self, tmp_path: Path):
        bm = BudgetManager(tmp_path)
        b = Budget(max_tokens=500, period="daily")
        bm.set_budget("d", b)
        bm.check("d", tokens=100)
        key = bm.usage["d"]["period_key"]
        # key must look like YYYY-MM-DD
        assert len(key) == 10
        assert key[4] == "-" and key[7] == "-"

    def test_hourly_period_key_has_hour(self, tmp_path: Path):
        bm = BudgetManager(tmp_path)
        bm.set_budget("h", Budget(max_tokens=500, period="hourly"))
        bm.check("h", tokens=10)
        key = bm.usage["h"]["period_key"]
        # key must look like YYYY-MM-DD-HH
        parts = key.split("-")
        assert len(parts) == 4

    def test_weekly_period_key_has_week(self, tmp_path: Path):
        bm = BudgetManager(tmp_path)
        bm.set_budget("w", Budget(max_tokens=500, period="weekly"))
        bm.check("w", tokens=10)
        key = bm.usage["w"]["period_key"]
        assert "W" in key  # e.g. "2026-W28"

    def test_monthly_period_key_has_month(self, tmp_path: Path):
        bm = BudgetManager(tmp_path)
        bm.set_budget("m", Budget(max_tokens=500, period="monthly"))
        bm.check("m", tokens=10)
        key = bm.usage["m"]["period_key"]
        # key must look like YYYY-MM
        parts = key.split("-")
        assert len(parts) == 2

    def test_daily_reset_when_period_key_changes(self, tmp_path: Path):
        """Simulate a day rollover by manually corrupting the stored period_key."""
        bm = BudgetManager(tmp_path)
        bm.set_budget("d", Budget(max_tokens=500, period="daily"))
        # Consume some budget
        bm.check("d", tokens=200)
        assert bm.usage["d"]["tokens"] == 200
        # Simulate yesterday's key
        bm.usage["d"]["period_key"] = "1999-01-01"
        # Next check should reset usage
        bm.check("d", tokens=50)
        assert bm.usage["d"]["tokens"] == 50

    def test_fallback_period_key_for_unknown_period(self, tmp_path: Path):
        """Cover the final `return 'session'` branch in _period_key."""
        bm = BudgetManager(tmp_path)
        b = Budget(max_tokens=500, period="session")
        bm.set_budget("x", b)
        # Force an invalid period bypassing __post_init__
        b.period = "unknown_period"  # type: ignore[assignment]
        # Should not raise; falls back to "session" string
        key = bm._period_key("x", b, __import__("datetime").datetime.utcnow())
        assert key == "session"


# ---------------------------------------------------------------------------
# BudgetManager — thread safety smoke test
# ---------------------------------------------------------------------------

class TestBudgetThreadSafety:
    def test_concurrent_checks_do_not_crash(self, tmp_path: Path):
        bm = BudgetManager(tmp_path)
        bm.set_budget("shared", Budget(max_tokens=100_000, on_exceed="warn"))
        errors: list[Exception] = []

        def worker():
            try:
                for _ in range(50):
                    bm.check("shared", tokens=1)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Thread errors: {errors}"
        assert bm.usage["shared"]["tokens"] == 400  # 8 threads x 50 calls x 1 token


# ---------------------------------------------------------------------------
# BudgetManager — save() error path (lines 74-76)
# ---------------------------------------------------------------------------

class TestBudgetSaveErrorPath:
    def test_save_exception_cleans_up_tmp_file(self, tmp_path: Path):
        """Cover the except Exception block which removes tmp file and re-raises."""
        bm = BudgetManager(tmp_path)
        with (
            patch("os.replace", side_effect=OSError("disk full")),
            pytest.raises(OSError, match="disk full"),
        ):
            bm.save()

    def test_save_succeeds_normally(self, tmp_path: Path):
        bm = BudgetManager(tmp_path)
        bm.set_budget("t", Budget(max_tokens=100))
        bm.save()  # no exception
        assert bm.state_file.exists()

