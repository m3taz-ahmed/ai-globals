"""Tests for runtime/schemas.py — Pydantic validation schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from runtime.schemas import BudgetSchema, PolicyFileSchema, PolicyRuleSchema


class TestBudgetSchema:
    """Tests for BudgetSchema validation."""

    def test_defaults(self) -> None:
        schema = BudgetSchema()
        assert schema.max_tokens is None
        assert schema.max_cost_usd is None
        assert schema.max_calls is None
        assert schema.period == "session"
        assert schema.on_exceed == "block"
        assert schema.fallback_model is None
        assert schema.rollout_max_tokens is None
        assert schema.rollout_reminder_threshold is None
        assert schema.token_weight_input == 1.0
        assert schema.token_weight_output == 1.0

    def test_valid_period_values(self) -> None:
        for period in ("session", "hourly", "daily", "weekly", "monthly"):
            schema = BudgetSchema(period=period)
            assert schema.period == period

    def test_invalid_period_raises(self) -> None:
        with pytest.raises(ValidationError):
            BudgetSchema(period="invalid")

    def test_valid_on_exceed_values(self) -> None:
        for action in ("warn", "fallback", "block"):
            schema = BudgetSchema(on_exceed=action)
            assert schema.on_exceed == action

    def test_invalid_on_exceed_raises(self) -> None:
        with pytest.raises(ValidationError):
            BudgetSchema(on_exceed="invalid")

    def test_max_tokens(self) -> None:
        schema = BudgetSchema(max_tokens=1000)
        assert schema.max_tokens == 1000

    def test_max_cost_usd(self) -> None:
        schema = BudgetSchema(max_cost_usd=10.5)
        assert schema.max_cost_usd == 10.5

    def test_rollout_fields(self) -> None:
        schema = BudgetSchema(rollout_max_tokens=500, rollout_reminder_threshold=0.8)
        assert schema.rollout_max_tokens == 500
        assert schema.rollout_reminder_threshold == 0.8

    def test_token_weights(self) -> None:
        schema = BudgetSchema(token_weight_input=0.5, token_weight_output=2.0)
        assert schema.token_weight_input == 0.5
        assert schema.token_weight_output == 2.0

    def test_extra_fields_allowed(self) -> None:
        schema = BudgetSchema(custom_field="value")  # type: ignore[call-arg]
        assert schema.model_dump().get("custom_field") == "value"


class TestPolicyRuleSchema:
    """Tests for PolicyRuleSchema validation."""

    def test_valid_rule(self) -> None:
        rule = PolicyRuleSchema(name="test", condition="True", action="allow")
        assert rule.name == "test"
        assert rule.condition == "True"
        assert rule.action == "allow"
        assert rule.description == ""
        assert rule.approvers == []

    def test_valid_actions(self) -> None:
        for action in ("allow", "ask", "deny"):
            rule = PolicyRuleSchema(name="r", condition="c", action=action)
            assert rule.action == action

    def test_invalid_action_raises(self) -> None:
        with pytest.raises(ValidationError):
            PolicyRuleSchema(name="r", condition="c", action="invalid")

    def test_empty_name_raises(self) -> None:
        with pytest.raises(ValidationError):
            PolicyRuleSchema(name="", condition="c", action="allow")

    def test_empty_condition_raises(self) -> None:
        with pytest.raises(ValidationError):
            PolicyRuleSchema(name="r", condition="", action="allow")

    def test_with_description_and_approvers(self) -> None:
        rule = PolicyRuleSchema(
            name="r", condition="c", action="ask",
            description="test rule", approvers=["alice", "bob"]
        )
        assert rule.description == "test rule"
        assert rule.approvers == ["alice", "bob"]


class TestPolicyFileSchema:
    """Tests for PolicyFileSchema validation."""

    def test_defaults(self) -> None:
        schema = PolicyFileSchema()
        assert schema.name == "default"
        assert schema.api_version == "governance.ai-global-os/v1"
        assert schema.default_action == "ask"
        assert schema.rules == []

    def test_valid_default_actions(self) -> None:
        for action in ("allow", "ask", "deny"):
            schema = PolicyFileSchema(default_action=action)
            assert schema.default_action == action

    def test_invalid_default_action_raises(self) -> None:
        with pytest.raises(ValidationError):
            PolicyFileSchema(default_action="invalid")

    def test_with_rules(self) -> None:
        rule = PolicyRuleSchema(name="r", condition="c", action="allow")
        schema = PolicyFileSchema(rules=[rule])
        assert len(schema.rules) == 1
        assert schema.rules[0].name == "r"

    def test_custom_name(self) -> None:
        schema = PolicyFileSchema(name="custom-policy")
        assert schema.name == "custom-policy"

    def test_custom_api_version(self) -> None:
        schema = PolicyFileSchema(api_version="custom/v2")
        assert schema.api_version == "custom/v2"
