"""Tests for runtime/budget_escalation.py — multi-stage budget escalation.

FAST tier — no MCP, no kernel, no model loading.
"""

from __future__ import annotations

from runtime.budget_escalation import (
    EscalationConfig,
    EscalationDirective,
    EscalationStage,
    compute_escalation,
    format_directive_message,
    is_budget_exceeded,
    recomputed_budget_flags,
    should_stop_subagent,
)


class TestComputeEscalation:
    def test_below_first_band_returns_none(self) -> None:
        result = compute_escalation(spend=50.0, limit=100.0, is_root=True)
        assert result is None

    def test_notice_band(self) -> None:
        result = compute_escalation(spend=71.0, limit=100.0, is_root=True)
        assert result is not None
        assert result.stage == EscalationStage.NOTICE

    def test_urgent_band(self) -> None:
        result = compute_escalation(spend=86.0, limit=100.0, is_root=True)
        assert result is not None
        assert result.stage == EscalationStage.URGENT

    def test_critical_band(self) -> None:
        result = compute_escalation(spend=96.0, limit=100.0, is_root=True)
        assert result is not None
        assert result.stage == EscalationStage.CRITICAL

    def test_subagent_bands(self) -> None:
        result = compute_escalation(spend=76.0, limit=100.0, is_root=False)
        assert result is not None
        assert result.stage == EscalationStage.NOTICE

    def test_zero_limit_returns_none(self) -> None:
        assert compute_escalation(spend=10.0, limit=0.0) is None

    def test_directive_has_message(self) -> None:
        result = compute_escalation(spend=71.0, limit=100.0, is_root=True)
        assert result is not None
        assert result.message
        assert result.is_root is True


class TestShouldStopSubagent:
    def test_below_reserve(self) -> None:
        assert should_stop_subagent(spend=80.0, limit=100.0) is False

    def test_at_reserve(self) -> None:
        assert should_stop_subagent(spend=90.0, limit=100.0) is True

    def test_above_reserve(self) -> None:
        assert should_stop_subagent(spend=95.0, limit=100.0) is True

    def test_zero_limit(self) -> None:
        assert should_stop_subagent(spend=10.0, limit=0.0) is False


class TestIsBudgetExceeded:
    def test_at_limit(self) -> None:
        assert is_budget_exceeded(spend=100.0, limit=100.0) is True

    def test_below_limit(self) -> None:
        assert is_budget_exceeded(spend=50.0, limit=100.0) is False

    def test_zero_limit(self) -> None:
        assert is_budget_exceeded(spend=10.0, limit=0.0) is False


class TestRecomputedBudgetFlags:
    def test_both_false_below_reserve(self) -> None:
        stopped, reserve = recomputed_budget_flags(spend=50.0, limit=100.0)
        assert stopped is False
        assert reserve is False

    def test_reserve_true_at_90pct(self) -> None:
        stopped, reserve = recomputed_budget_flags(spend=90.0, limit=100.0)
        assert stopped is False
        assert reserve is True

    def test_both_true_at_limit(self) -> None:
        stopped, reserve = recomputed_budget_flags(spend=100.0, limit=100.0)
        assert stopped is True
        assert reserve is True


class TestFormatDirectiveMessage:
    def test_contains_label_and_pct(self) -> None:
        directive = EscalationDirective(
            stage=EscalationStage.NOTICE,
            label="NOTICE",
            message="Begin wind-down.",
            utilization=0.71,
            is_root=True,
        )
        msg = format_directive_message(directive)
        assert "NOTICE" in msg
        assert "71%" in msg
        assert "Begin wind-down" in msg


class TestCustomConfig:
    def test_custom_bands(self) -> None:
        config = EscalationConfig(
            root_bands=(0.50, 0.70, 0.90),
            subagent_bands=(0.50, 0.60, 0.70),
            subagent_reserve=0.80,
        )
        result = compute_escalation(spend=55.0, limit=100.0, is_root=True, config=config)
        assert result is not None
        assert result.stage == EscalationStage.NOTICE
        assert should_stop_subagent(spend=81.0, limit=100.0, config=config) is True
