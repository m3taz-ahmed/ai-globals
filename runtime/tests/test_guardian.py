#!/usr/bin/env python3
"""Tests for runtime.guardian."""

from __future__ import annotations

import asyncio

import pytest

from runtime.guardian import (
    ActionRequest,
    ApprovalRequiredError,
    DecisionStatus,
    GuardConfig,
    Guardian,
    ainvoke,
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


# ---------------------------------------------------------------------------
# _PredicateEvaluator._resolve — line 98 (non-dict traversal returns None)
# ---------------------------------------------------------------------------

def test_resolve_returns_none_for_non_dict_traversal():
    """When traversing a dotted key and an intermediate value is not a dict, returns None."""
    g = Guardian(
        [
            {
                "name": "test",
                "decision": "deny",
                "all": [{"key": "resource.environment", "op": "eq", "value": "prod"}],
            }
        ]
    )
    # 'resource' is a string, not a dict — _resolve should return None
    d = g.authorize(ActionRequest(tool="x", attributes={"resource": "not-a-dict"}))
    assert d.status == DecisionStatus.ALLOW  # no match because None != "prod"


# ---------------------------------------------------------------------------
# evaluate_predicate — line 106 (key is None returns False)
# ---------------------------------------------------------------------------

def test_predicate_with_none_key_returns_false():
    """A predicate with no 'key' field returns False (no match)."""
    g = Guardian(
        [
            {
                "name": "test",
                "decision": "deny",
                "all": [{"op": "eq", "value": "prod"}],  # missing 'key'
            }
        ]
    )
    d = g.authorize(ActionRequest(tool="x", attributes={"env": "prod"}))
    assert d.status == DecisionStatus.ALLOW  # no match because key is None


# ---------------------------------------------------------------------------
# evaluate_predicate — line 110 (unsupported operator raises ValueError)
# ---------------------------------------------------------------------------

def test_unsupported_operator_raises_value_error():
    """An unsupported operator raises ValueError when evaluated directly."""
    from runtime.guardian import _PredicateEvaluator

    evaluator = _PredicateEvaluator({"env": "prod"})
    with pytest.raises(ValueError, match="Unsupported operator"):
        evaluator.evaluate_predicate({"key": "env", "op": "regex", "value": "prod"})


# ---------------------------------------------------------------------------
# from_yaml — lines 129-130
# ---------------------------------------------------------------------------

def test_from_yaml(tmp_path):
    """Guardian.from_yaml loads rules from a YAML file."""
    import yaml

    yaml_file = tmp_path / "policy.yaml"
    yaml_file.write_text(
        yaml.dump({"rules": [{"name": "deny_all", "tool": "delete", "decision": "deny"}]}),
        encoding="utf-8",
    )
    g = Guardian.from_yaml(str(yaml_file))
    d = g.authorize(ActionRequest(tool="delete"))
    assert d.status == DecisionStatus.DENY
    assert d.rule_name == "deny_all"


def test_from_yaml_empty_file(tmp_path):
    """Guardian.from_yaml handles empty YAML files."""
    yaml_file = tmp_path / "empty.yaml"
    yaml_file.write_text("", encoding="utf-8")
    g = Guardian.from_yaml(str(yaml_file))
    assert g.rules == []


# ---------------------------------------------------------------------------
# from_json — lines 134-135
# ---------------------------------------------------------------------------

def test_from_json(tmp_path):
    """Guardian.from_json loads rules from a JSON file."""
    import json

    json_file = tmp_path / "policy.json"
    json_file.write_text(
        json.dumps({"rules": [{"name": "deny_all", "tool": "delete", "decision": "deny"}]}),
        encoding="utf-8",
    )
    g = Guardian.from_json(str(json_file))
    d = g.authorize(ActionRequest(tool="delete"))
    assert d.status == DecisionStatus.DENY
    assert d.rule_name == "deny_all"


# ---------------------------------------------------------------------------
# Tool mismatch continues to next rule — line 143
# ---------------------------------------------------------------------------

def test_tool_mismatch_continues_to_next_rule():
    """When a rule's tool doesn't match, evaluation continues to the next rule."""
    g = Guardian(
        [
            {"name": "rule_a", "tool": "tool_a", "decision": "deny"},
            {"name": "rule_b", "tool": "tool_b", "decision": "allow"},
        ]
    )
    d = g.authorize(ActionRequest(tool="tool_b"))
    assert d.status == DecisionStatus.ALLOW
    assert d.rule_name == "rule_b"


# ---------------------------------------------------------------------------
# Single predicate rule — line 152
# ---------------------------------------------------------------------------

def test_single_predicate_rule():
    """A rule with a 'predicate' key (not 'all' or 'any') is evaluated."""
    g = Guardian(
        [
            {
                "name": "block_prod",
                "decision": "deny",
                "predicate": {"key": "env", "op": "eq", "value": "prod"},
            }
        ]
    )
    d = g.authorize(ActionRequest(tool="x", attributes={"env": "prod"}))
    assert d.status == DecisionStatus.DENY
    assert d.rule_name == "block_prod"

    d = g.authorize(ActionRequest(tool="x", attributes={"env": "dev"}))
    assert d.status == DecisionStatus.ALLOW


# ---------------------------------------------------------------------------
# Rule with no predicate/all/any — line 154 (matched=True)
# ---------------------------------------------------------------------------

def test_rule_with_no_matcher_always_matches():
    """A rule with no 'all', 'any', or 'predicate' always matches."""
    g = Guardian([{"name": "catch_all", "tool": "x", "decision": "deny"}])
    d = g.authorize(ActionRequest(tool="x", attributes={}))
    assert d.status == DecisionStatus.DENY
    assert d.rule_name == "catch_all"


# ---------------------------------------------------------------------------
# Evaluation error handling — lines 155-160
# ---------------------------------------------------------------------------

def test_evaluation_error_denies():
    """When evaluation raises and on_evaluation_error is DENY, returns DENY."""
    g = Guardian(
        [{"name": "bad_op", "decision": "deny", "all": [{"key": "x", "op": "bad_op", "value": 1}]}],
        config=GuardConfig(on_evaluation_error=DecisionStatus.DENY),
    )
    d = g.authorize(ActionRequest(tool="x", attributes={"x": 1}))
    assert d.status == DecisionStatus.DENY
    assert d.reason == "evaluation error"


def test_evaluation_error_require_approval():
    """When evaluation raises and on_evaluation_error is REQUIRE_APPROVAL, returns REQUIRE_APPROVAL."""
    g = Guardian(
        [{"name": "bad_op", "decision": "deny", "all": [{"key": "x", "op": "bad_op", "value": 1}]}],
        config=GuardConfig(on_evaluation_error=DecisionStatus.REQUIRE_APPROVAL),
    )
    d = g.authorize(ActionRequest(tool="x", attributes={"x": 1}))
    assert d.status == DecisionStatus.REQUIRE_APPROVAL
    assert d.reason == "evaluation error"


def test_evaluation_error_allow_continues():
    """When evaluation raises and on_evaluation_error is ALLOW, continues to next rule."""
    g = Guardian(
        [
            {"name": "bad_op", "decision": "deny", "all": [{"key": "x", "op": "bad_op", "value": 1}]},
            {"name": "fallback", "tool": "x", "decision": "allow"},
        ],
        config=GuardConfig(on_evaluation_error=DecisionStatus.ALLOW),
    )
    d = g.authorize(ActionRequest(tool="x", attributes={"x": 1}))
    assert d.status == DecisionStatus.ALLOW
    assert d.rule_name == "fallback"


# ---------------------------------------------------------------------------
# Async invoke decorator — lines 202-210, 213
# ---------------------------------------------------------------------------

def test_invoke_decorator_async():
    """invoke decorator wraps async functions with async_wrapper."""
    g = Guardian(
        [{"name": "no_delete", "tool": "delete", "decision": "deny", "all": [{"key": "env", "op": "eq", "value": "prod"}]}]
    )

    @invoke(g)
    async def delete(env: str) -> str:
        return f"deleted in {env}"

    result = asyncio.get_event_loop().run_until_complete(delete("dev"))
    assert result == "deleted in dev"

    with pytest.raises(PermissionError):
        asyncio.get_event_loop().run_until_complete(delete("prod"))


def test_invoke_decorator_async_require_approval():
    """async invoke decorator raises ApprovalRequiredError when required."""
    g = Guardian(
        [{"name": "approve", "tool": "spend", "decision": "require_approval", "all": [{"key": "amount", "op": "gt", "value": 100}]}]
    )

    @invoke(g)
    async def spend(amount: int) -> int:
        return amount  # pragma: no cover

    with pytest.raises(ApprovalRequiredError):
        asyncio.get_event_loop().run_until_complete(spend(200))


def test_invoke_decorator_async_require_approval_allowed():
    """Cover line 332: return amount when approval is NOT required (amount <= 100)."""
    g = Guardian(
        [{"name": "approve", "tool": "spend", "decision": "require_approval", "all": [{"key": "amount", "op": "gt", "value": 100}]}]
    )

    @invoke(g)
    async def spend(amount: int) -> int:
        return amount

    result = asyncio.get_event_loop().run_until_complete(spend(50))
    assert result == 50


# ---------------------------------------------------------------------------
# ainvoke — line 221
# ---------------------------------------------------------------------------

def test_ainvoke_decorator():
    """ainvoke is an alias for invoke that works on sync functions."""
    g = Guardian(
        [{"name": "no_delete", "tool": "delete", "decision": "deny", "all": [{"key": "env", "op": "eq", "value": "prod"}]}]
    )

    @ainvoke(g)
    def delete(env: str) -> str:
        return f"deleted in {env}"

    assert delete("dev") == "deleted in dev"
    with pytest.raises(PermissionError):
        delete("prod")


def test_ainvoke_decorator_async():
    """ainvoke works on async functions too."""
    g = Guardian([])

    @ainvoke(g)
    async def read(path: str) -> str:
        return f"read {path}"

    result = asyncio.get_event_loop().run_until_complete(read("/tmp"))
    assert result == "read /tmp"


# ---------------------------------------------------------------------------
# check() raises PermissionError on deny — line 177
# ---------------------------------------------------------------------------

def test_check_raises_permission_error_on_deny():
    """check() raises PermissionError when decision is DENY."""
    g = Guardian([{"name": "deny_all", "tool": "x", "decision": "deny"}])
    with pytest.raises(PermissionError, match="Policy denied"):
        g.check(ActionRequest(tool="x"))


# ---------------------------------------------------------------------------
# invoke with explicit tool name
# ---------------------------------------------------------------------------

def test_invoke_with_explicit_tool_name():
    """invoke decorator uses the explicitly provided tool name."""
    g = Guardian([{"name": "deny_custom", "tool": "my_tool", "decision": "deny"}])

    @invoke(g, tool="my_tool")
    def my_func(x: int) -> int:
        return x  # pragma: no cover

    with pytest.raises(PermissionError):
        my_func(1)


def test_invoke_with_explicit_tool_name_allowed():
    """Cover line 390: return x when the guardian allows the call."""
    g = Guardian(
        [{"name": "deny_prod", "tool": "my_tool", "decision": "deny", "all": [{"key": "env", "op": "eq", "value": "prod"}]}]
    )

    @invoke(g, tool="my_tool")
    def my_func(x: int) -> int:
        return x

    # No attributes → no match → allowed
    assert my_func(42) == 42
