"""Tests for runtime/mcp_firewall.py."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from runtime.mcp_firewall import (
    FirewallAction,
    McpFirewall,
    ToolAccessRule,
    _eval_node,
    _safe_eval,
)


class TestSafeEval:
    def test_literal(self):
        assert _safe_eval("True", {}) is True

    def test_name_lookup(self):
        assert _safe_eval("x", {"x": 5}) is True  # bool(5) == True

    def test_equality(self):
        assert _safe_eval('q == "secret"', {"q": "secret"}) is True
        assert _safe_eval('q == "secret"', {"q": "public"}) is False

    def test_in_operator(self):
        assert _safe_eval('q in ["a", "b"]', {"q": "a"}) is True
        assert _safe_eval('q in ["a", "b"]', {"q": "c"}) is False

    def test_in_string(self):
        assert _safe_eval('"rm" in cmd', {"cmd": "rm -rf /"}) is True

    def test_boolean_and(self):
        assert _safe_eval('a and b', {"a": True, "b": True}) is True
        assert _safe_eval('a and b', {"a": True, "b": False}) is False

    def test_attribute_access_truthy(self):
        obj = type("O", (), {"value": 7})()
        assert _safe_eval("obj.value", {"obj": obj}) is True  # bool(7)

    def test_subscript_truthy(self):
        assert _safe_eval("d[0]", {"d": [10, 20]}) is True  # bool(10)

    def test_rejects_call(self):
        with pytest.raises(ValueError):
            _safe_eval("open('x')", {})

    def test_syntax_error_returns_false(self):
        assert _safe_eval("not valid !!!", {}) is False


class TestEvalNodeRaw:
    """Test _eval_node returns raw values (not bool-wrapped)."""

    def test_name_returns_raw(self):
        assert _eval_node(__import__("ast").parse("x", mode="eval").body, {"x": 5}) == 5

    def test_subscript_list(self):
        import ast

        node = ast.parse("d[0]", mode="eval").body
        assert _eval_node(node, {"d": [10, 20]}) == 10

    def test_subscript_dict(self):
        import ast

        node = ast.parse('d["k"]', mode="eval").body
        assert _eval_node(node, {"d": {"k": 99}}) == 99


class TestToolAccessRule:
    def test_exact_match(self):
        r = ToolAccessRule(name="r", tool="search_memory", action=FirewallAction.DENY)
        assert r.matches_tool("search_memory")
        assert not r.matches_tool("search_rules")

    def test_wildcard_prefix(self):
        r = ToolAccessRule(name="r", tool="search_*", action=FirewallAction.DENY)
        assert r.matches_tool("search_memory")
        assert r.matches_tool("search_rules")
        assert not r.matches_tool("deploy_app")

    def test_wildcard_suffix(self):
        r = ToolAccessRule(name="r", tool="*_tools", action=FirewallAction.ALLOW)
        assert r.matches_tool("memory_tools")
        assert not r.matches_tool("memory_resources")

    def test_star_matches_all(self):
        r = ToolAccessRule(name="r", tool="*", action=FirewallAction.ALLOW)
        assert r.matches_tool("anything")


class TestMcpFirewall:
    def test_no_rules_default_allow(self):
        fw = McpFirewall()
        v = fw.evaluate("any_tool", {})
        assert v.action is FirewallAction.ALLOW
        assert v.rule_name == "default"

    def test_first_match_wins(self):
        fw = McpFirewall(
            rules=[
                ToolAccessRule(name="low", tool="*", action=FirewallAction.ALLOW, priority=1),
                ToolAccessRule(name="high", tool="*", action=FirewallAction.DENY, priority=10),
            ]
        )
        v = fw.evaluate("any", {})
        assert v.action is FirewallAction.DENY
        assert v.rule_name == "high"

    def test_condition_filters_match(self):
        fw = McpFirewall(
            rules=[
                ToolAccessRule(
                    name="deny-secret",
                    tool="search_memory",
                    action=FirewallAction.DENY,
                    condition='query == "secret"',
                    priority=10,
                ),
            ]
        )
        assert fw.evaluate("search_memory", {"query": "secret"}).action is FirewallAction.DENY
        assert fw.evaluate("search_memory", {"query": "public"}).action is FirewallAction.ALLOW

    def test_require_approval(self):
        fw = McpFirewall(
            rules=[
                ToolAccessRule(name="appr", tool="deploy_*", action=FirewallAction.REQUIRE_APPROVAL),
            ]
        )
        v = fw.evaluate("deploy_app", {})
        assert v.action is FirewallAction.REQUIRE_APPROVAL

    def test_check_returns_decision_dict(self):
        fw = McpFirewall(
            rules=[ToolAccessRule(name="d", tool="x", action=FirewallAction.DENY)]
        )
        result = fw.check("x", {})
        assert result["decision"] == "deny"
        assert result["rule"] == "d"

    def test_check_maps_require_approval_to_ask(self):
        fw = McpFirewall(
            rules=[ToolAccessRule(name="a", tool="x", action=FirewallAction.REQUIRE_APPROVAL)]
        )
        assert fw.check("x", {})["decision"] == "ask"

    def test_denials_counter(self):
        fw = McpFirewall(
            rules=[ToolAccessRule(name="d", tool="x", action=FirewallAction.DENY)]
        )
        fw.evaluate("x", {})
        fw.evaluate("x", {})
        assert fw.denials == {"d": 2}

    def test_add_rule_inserts_by_priority(self):
        fw = McpFirewall(rules=[ToolAccessRule(name="a", tool="x", action=FirewallAction.ALLOW, priority=1)])
        fw.add_rule(ToolAccessRule(name="b", tool="x", action=FirewallAction.DENY, priority=5))
        assert fw.evaluate("x", {}).rule_name == "b"


class TestFromYaml:
    def test_load_valid_file(self, tmp_path: Path):
        cfg = tmp_path / "fw.yaml"
        cfg.write_text(
            yaml.dump({
                "default_action": "deny",
                "rules": [
                    {"name": "allow-reads", "tool": "get_*", "action": "allow", "priority": 10},
                    {"name": "deny-writes", "tool": "set_*", "action": "deny", "condition": 'env == "prod"'},
                ],
            }),
            encoding="utf-8",
        )
        fw = McpFirewall.from_yaml(cfg)
        assert fw.default_action is FirewallAction.DENY
        assert fw.evaluate("get_status", {}) is not None
        assert fw.evaluate("get_status", {}).action is FirewallAction.ALLOW
        assert fw.evaluate("set_config", {"env": "prod"}).action is FirewallAction.DENY
        assert fw.evaluate("set_config", {"env": "dev"}).action is FirewallAction.DENY  # default

    def test_missing_file_returns_default(self, tmp_path: Path):
        fw = McpFirewall.from_yaml(tmp_path / "nope.yaml")
        assert fw.default_action is FirewallAction.ALLOW
        assert len(fw.rules) == 0

    def test_malformed_rule_skipped(self, tmp_path: Path):
        cfg = tmp_path / "fw.yaml"
        cfg.write_text(
            yaml.dump({
                "rules": [
                    {"name": "ok", "tool": "x", "action": "allow"},
                    {"tool": "missing-name"},  # malformed — skipped
                    {"name": "bad-action", "tool": "y", "action": "explode"},  # bad enum
                ],
            }),
            encoding="utf-8",
        )
        fw = McpFirewall.from_yaml(cfg)
        assert len(fw.rules) == 1
        assert fw.rules[0].name == "ok"


class TestOsPolicyFile:
    """Verify the shipped OS-level mcp_firewall.yaml loads cleanly."""

    def test_os_firewall_loads(self):
        # runtime/tests/test_mcp_firewall.py -> runtime/policies/mcp_firewall.yaml
        path = Path(__file__).resolve().parent.parent / "policies" / "mcp_firewall.yaml"
        fw = McpFirewall.from_yaml(path)
        assert len(fw.rules) >= 3
        # Destructive rule should block rm -rf
        v = fw.evaluate("exec_shell", {"command": "rm -rf /"})
        assert v.action is FirewallAction.DENY
