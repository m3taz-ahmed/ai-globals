"""Gap coverage for runtime/mcp_firewall.py - McpFirewall paths."""

from __future__ import annotations

from runtime.mcp_firewall import (
    FirewallAction,
    McpFirewall,
    ToolAccessRule,
)


class TestEvaluate:
    def test_no_rules_matches_default(self):
        fw = McpFirewall()
        v = fw.evaluate("any_tool", {})
        assert v.action is FirewallAction.ALLOW
        assert v.rule_name == "default"

    def test_tool_pattern_mismatch_skips(self):
        fw = McpFirewall([ToolAccessRule("r1", "other_tool", FirewallAction.DENY)])
        v = fw.evaluate("my_tool", {})
        assert v.action is FirewallAction.ALLOW

    def test_condition_true_matches(self):
        rule = ToolAccessRule(
            "r1", "search_*", FirewallAction.DENY, condition="q == 'x'"
        )
        fw = McpFirewall([rule])
        v = fw.evaluate("search_memory", {"q": "x"})
        assert v.action is FirewallAction.DENY
        assert v.matched_condition == "q == 'x'"
        assert fw.denials == {"r1": 1}

    def test_condition_false_skips(self):
        rule = ToolAccessRule(
            "r1", "t", FirewallAction.DENY, condition="q == 'x'"
        )
        fw = McpFirewall([rule])
        assert fw.evaluate("t", {"q": "y"}).action is FirewallAction.ALLOW

    def test_condition_error_deny_fails_closed(self):
        rule = ToolAccessRule(
            "broken", "t", FirewallAction.DENY, condition="x is y"
        )
        fw = McpFirewall([rule])
        v = fw.evaluate("t", {})
        assert v.action is FirewallAction.DENY
        assert "condition_error" in v.reason

    def test_condition_error_allow_is_skipped(self):
        rule = ToolAccessRule(
            "broken", "t", FirewallAction.ALLOW, condition="x is y"
        )
        fw = McpFirewall([rule])
        v = fw.evaluate("t", {})
        assert v.rule_name == "default"

    def test_rule_without_condition(self):
        rule = ToolAccessRule("r1", "t", FirewallAction.REQUIRE_APPROVAL)
        fw = McpFirewall([rule])
        assert fw.evaluate("t", {}).action is FirewallAction.REQUIRE_APPROVAL

    def test_add_rule_and_properties(self):
        fw = McpFirewall()
        fw.add_rule(ToolAccessRule("z", "t", FirewallAction.DENY, priority=5))
        fw.add_rule(ToolAccessRule("a", "t", FirewallAction.ALLOW, priority=9))
        names = [r.name for r in fw.rules]
        assert names == ["a", "z"]  # priority desc


class TestCheck:
    def test_check_maps_deny(self):
        fw = McpFirewall([ToolAccessRule("r", "t", FirewallAction.DENY)])
        out = fw.check("t", {})
        assert out["decision"] == "deny"
        assert out["tool"] == "t"

    def test_check_maps_ask(self):
        fw = McpFirewall(
            [ToolAccessRule("r", "t", FirewallAction.REQUIRE_APPROVAL)]
        )
        assert fw.check("t", {})["decision"] == "ask"


class TestFromYaml:
    def test_missing_file_returns_empty(self, tmp_path):
        fw = McpFirewall.from_yaml(tmp_path / "nope.yaml")
        assert fw.rules == []

    def test_malformed_rule_skipped(self, tmp_path):
        f = tmp_path / "fw.yaml"
        f.write_text(
            "default_action: deny\n"
            "rules:\n"
            "  - name: ok\n    tool: t\n    action: deny\n"
            "  - name: bad\n    tool: t\n    action: notanaction\n"
            "  - tool: noname\n    action: allow\n",
            encoding="utf-8",
        )
        fw = McpFirewall.from_yaml(f)
        assert fw.default_action is FirewallAction.DENY
        assert [r.name for r in fw.rules] == ["ok"]

    def test_empty_yaml(self, tmp_path):
        f = tmp_path / "fw.yaml"
        f.write_text("", encoding="utf-8")
        fw = McpFirewall.from_yaml(f)
        assert fw.default_action is FirewallAction.ALLOW
