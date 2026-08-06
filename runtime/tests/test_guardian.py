#!/usr/bin/env python3
"""Tests for runtime.guardian."""

from __future__ import annotations

import pytest

from runtime.guardian import (
    ActionRequest,
    ApprovalRequiredError,
    DecisionStatus,
    GuardConfig,
    Guardian,
    invoke,
)


def test_allow_default():
    g = Guardian([])
    d = g.authorize(ActionRequest(tool="resource.delete"))
    assert d.status == DecisionStatus.ALLOW


def test_deny_by_tool_and_attributes():
    g = Guardian(
        [
            {
                "name": "block_risky_delete",
                "tool": "resource.delete",
                "decision": "deny",
                "all": [
                    {"key": "resource.environment", "op": "eq", "value": "prod"},
                    {"key": "context.risk_level", "op": "eq", "value": "high"},
                ],
            }
        ]
    )
    d = g.authorize(
        ActionRequest(
            tool="resource.delete",
            attributes={"resource": {"environment": "prod"}, "context": {"risk_level": "high"}},
        )
    )
    assert d.status == DecisionStatus.DENY
    assert d.rule_name == "block_risky_delete"

    d = g.authorize(
        ActionRequest(
            tool="resource.delete",
            attributes={"resource": {"environment": "dev"}, "context": {"risk_level": "high"}},
        )
    )
    assert d.status == DecisionStatus.ALLOW


def test_any_matcher():
    g = Guardian(
        [
            {
                "name": "block_dangerous",
                "decision": "deny",
                "any": [
                    {"key": "env", "op": "eq", "value": "prod"},
                    {"key": "risk", "op": "eq", "value": "high"},
                ],
            }
        ]
    )
    assert g.authorize(ActionRequest(tool="x", attributes={"env": "prod"})).status == DecisionStatus.DENY
    assert g.authorize(ActionRequest(tool="x", attributes={"risk": "high"})).status == DecisionStatus.DENY
    assert g.authorize(ActionRequest(tool="x", attributes={"env": "dev"})).status == DecisionStatus.ALLOW


def test_approve_required():
    g = Guardian(
        [
            {
                "name": "approve_costly",
                "tool": "budget.spend",
                "decision": "require_approval",
                "all": [{"key": "amount", "op": "gt", "value": 100}],
            }
        ]
    )
    with pytest.raises(ApprovalRequiredError):
        g.check(ActionRequest(tool="budget.spend", attributes={"amount": 500}))

    g.check(ActionRequest(tool="budget.spend", attributes={"amount": 50}))  # allow


def test_invoke_decorator():
    g = Guardian(
        [{"name": "no_delete", "tool": "delete", "decision": "deny", "all": [{"key": "env", "op": "eq", "value": "prod"}]}]
    )

    @invoke(g)
    def delete(env: str) -> str:
        return f"deleted in {env}"

    assert delete("dev") == "deleted in dev"
    with pytest.raises(PermissionError):
        delete("prod")


def test_default_action_config():
    g = Guardian([], config=GuardConfig(default_decision=DecisionStatus.DENY))
    assert g.authorize(ActionRequest(tool="x")).status == DecisionStatus.DENY
