"""Tests for guardian kill-switch rules (from agent-trace)."""

from __future__ import annotations

from runtime.guardian import (
    ActionRequest,
    DecisionStatus,
    Guardian,
    KillSwitchRule,
)


def test_kill_switch_cost_ceiling() -> None:
    rule = KillSwitchRule(rule_type="cost_ceiling", limit=5.0)
    triggered, reason = rule.evaluate({"total_cost": 6.0})
    assert triggered is True
    assert "6.00" in reason


def test_kill_switch_cost_ceiling_not_triggered() -> None:
    rule = KillSwitchRule(rule_type="cost_ceiling", limit=5.0)
    triggered, _ = rule.evaluate({"total_cost": 3.0})
    assert triggered is False


def test_kill_switch_file_touched() -> None:
    rule = KillSwitchRule(rule_type="file_touched", pattern="protected/*")
    triggered, reason = rule.evaluate({"files_touched": ["protected/secret.key"]})
    assert triggered is True
    assert "protected/secret.key" in reason


def test_kill_switch_file_touched_no_match() -> None:
    rule = KillSwitchRule(rule_type="file_touched", pattern="protected/*")
    triggered, _ = rule.evaluate({"files_touched": ["public/index.html"]})
    assert triggered is False


def test_kill_switch_tool_call_count() -> None:
    rule = KillSwitchRule(rule_type="tool_call_count", limit=100)
    triggered, reason = rule.evaluate({"tool_call_count": 101})
    assert triggered is True
    assert "101" in reason


def test_kill_switch_time_limit() -> None:
    rule = KillSwitchRule(rule_type="time_limit", limit=300.0)
    triggered, reason = rule.evaluate({"elapsed_seconds": 310.0})
    assert triggered is True
    assert "310.0" in reason


def test_guardian_with_kill_switch_denies() -> None:
    ks = KillSwitchRule(rule_type="cost_ceiling", limit=5.0)
    guardian = Guardian(rules=[], kill_switch_rules=[ks])
    req = ActionRequest(tool="exec", attributes={"total_cost": 10.0})
    decision = guardian.authorize(req)
    assert decision.status is DecisionStatus.DENY
    assert "kill_switch" in decision.rule_name


def test_guardian_kill_switch_takes_precedence() -> None:
    # Even with an allow rule, kill-switch should deny
    ks = KillSwitchRule(rule_type="cost_ceiling", limit=5.0)
    guardian = Guardian(
        rules=[{"name": "allow_all", "tool": "exec", "decision": "allow"}],
        kill_switch_rules=[ks],
    )
    req = ActionRequest(tool="exec", attributes={"total_cost": 10.0})
    decision = guardian.authorize(req)
    assert decision.status is DecisionStatus.DENY


def test_guardian_no_kill_switch_allows() -> None:
    guardian = Guardian(rules=[{"name": "allow_all", "tool": "exec", "decision": "allow"}])
    req = ActionRequest(tool="exec", attributes={"total_cost": 10.0})
    decision = guardian.authorize(req)
    assert decision.status is DecisionStatus.ALLOW
