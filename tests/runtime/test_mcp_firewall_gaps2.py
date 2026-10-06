"""Gap coverage for runtime/mcp_firewall.py - AST evaluator + verdict edges."""

from __future__ import annotations

import pytest

from runtime.mcp_firewall import (
    FirewallAction,
    McpFirewall,
    McpFirewallError,
    ToolAccessRule,
    _safe_eval,
)
from runtime.schemas import PolicyDeniedError


class TestSafeEvalRemaining:
    def test_dict_attribute_access(self):
        assert _safe_eval("d.name == 'x'", {"d": {"name": "x"}}) is True

    def test_dunder_attribute_blocked(self):
        with pytest.raises(ValueError, match="dunder"):
            _safe_eval("d.__class__", {"d": {}})

    def test_binop_arithmetic(self):
        assert _safe_eval("a + b == 3", {"a": 1, "b": 2}) is True

    def test_binop_unsupported_op(self):
        with pytest.raises(ValueError, match="unsupported binop"):
            _safe_eval("a @ b", {"a": 1, "b": 2})

    def test_unaryop_not(self):
        assert _safe_eval("not flag", {"flag": False}) is True

    def test_unaryop_neg(self):
        assert _safe_eval("-n == -5", {"n": 5}) is True

    def test_unaryop_unsupported(self):
        with pytest.raises(ValueError, match="unsupported unaryop"):
            _safe_eval("~x", {"x": 1})

    def test_tuple_literal(self):
        assert _safe_eval("t == (1, 2)", {"t": (1, 2)}) is True

    def test_set_literal(self):
        assert _safe_eval("s == {1, 2}", {"s": {1, 2}}) is True

    def test_in_missing_var_is_false(self):
        assert _safe_eval("missing in ['a']", {}) is False

    def test_not_in_missing_var_is_true(self):
        assert _safe_eval("missing not in ['a']", {}) is True


class TestVerdictConversions:
    def test_require_approval_gate_verdict(self):
        fw = McpFirewall(
            [ToolAccessRule("r1", "t", FirewallAction.REQUIRE_APPROVAL)]
        )
        v = fw.evaluate("t", {})
        assert v.action is FirewallAction.REQUIRE_APPROVAL
        gv = v.to_gate_verdict()
        assert gv is not None

    def test_to_policy_denied(self):
        fw = McpFirewall([ToolAccessRule("r1", "t", FirewallAction.DENY)])
        v = fw.evaluate("t", {})
        err = fw.to_policy_denied(v)
        assert isinstance(err, PolicyDeniedError)

    def test_tool_middle_wildcard(self):
        rule = ToolAccessRule("r1", "*exec*", FirewallAction.DENY)
        fw = McpFirewall([rule])
        assert fw.evaluate("run_exec_now", {}).action is FirewallAction.DENY
        assert fw.evaluate("run_safe_now", {}).action is FirewallAction.ALLOW

    def test_mcp_firewall_error_init(self):
        err = McpFirewallError("bad config", context={"k": 1})
        assert err.error_code == "MCP_FIREWALL_ERROR"
