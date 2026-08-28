"""Tests for runtime.agent_baseline — behavioral anomaly detection."""

from __future__ import annotations

import pytest

from runtime.agent_baseline import (
    AgentAction,
    AgentBaseline,
    AnomalyType,
    BaselinePhase,
    BaselineRegistry,
)


@pytest.fixture
def baseline() -> AgentBaseline:
    return AgentBaseline(agent_id="test-agent")


def _make_action(tool: str = "search", action_type: str = "read", **kw) -> AgentAction:
    return AgentAction(tool_name=tool, action_type=action_type, **kw)


def test_starts_in_learning_phase(baseline: AgentBaseline) -> None:
    assert baseline.is_learning
    assert baseline.phase is BaselinePhase.LEARNING


def test_transitions_to_detecting(baseline: AgentBaseline) -> None:
    for i in range(AgentBaseline.LEARNING_THRESHOLD):
        baseline.observe(_make_action(tool=f"tool_{i % 3}"))
    assert baseline.phase is BaselinePhase.DETECTING
    assert not baseline.is_learning


def test_no_anomaly_during_learning(baseline: AgentBaseline) -> None:
    # During learning, check() always returns None
    assert baseline.check(_make_action(tool="never_seen")) is None


def test_detects_new_tool(baseline: AgentBaseline) -> None:
    # Learn with tool_a
    for _ in range(AgentBaseline.LEARNING_THRESHOLD):
        baseline.observe(_make_action(tool="tool_a"))
    # Now check with a new tool
    alert = baseline.check(_make_action(tool="tool_b"))
    assert alert is not None
    assert alert.anomaly_type is AnomalyType.NEW_TOOL
    assert alert.is_anomalous


def test_detects_new_data_source(baseline: AgentBaseline) -> None:
    for _ in range(AgentBaseline.LEARNING_THRESHOLD):
        baseline.observe(_make_action(tool="read_file", data_source="/safe/path"))
    alert = baseline.check(_make_action(tool="read_file", data_source="/etc/passwd"))
    assert alert is not None
    assert alert.anomaly_type is AnomalyType.NEW_DATA_SOURCE


def test_detects_new_endpoint(baseline: AgentBaseline) -> None:
    for _ in range(AgentBaseline.LEARNING_THRESHOLD):
        baseline.observe(_make_action(tool="fetch", endpoint="http://safe.com"))
    alert = baseline.check(_make_action(tool="fetch", endpoint="http://evil.com"))
    assert alert is not None
    assert alert.anomaly_type is AnomalyType.NEW_ENDPOINT
    assert alert.severity == 0.8


def test_no_anomaly_for_known_action(baseline: AgentBaseline) -> None:
    for _ in range(AgentBaseline.LEARNING_THRESHOLD):
        baseline.observe(_make_action(tool="search", action_type="read"))
    alert = baseline.check(_make_action(tool="search", action_type="read"))
    assert alert is None


def test_stats(baseline: AgentBaseline) -> None:
    baseline.observe(_make_action(tool="search"))
    baseline.observe(_make_action(tool="read"))
    stats = baseline.stats()
    assert stats["agent_id"] == "test-agent"
    assert stats["total_observations"] == 2
    assert stats["unique_tools"] == 2


def test_registry_get_or_create() -> None:
    reg = BaselineRegistry()
    bl1 = reg.get_or_create("agent-1")
    bl2 = reg.get_or_create("agent-1")
    assert bl1 is bl2
    bl3 = reg.get_or_create("agent-2")
    assert bl3 is not bl1


def test_registry_observe_and_check() -> None:
    reg = BaselineRegistry()
    for _ in range(AgentBaseline.LEARNING_THRESHOLD):
        reg.observe("agent-1", _make_action(tool="tool_a"))
    alert = reg.check("agent-1", _make_action(tool="tool_b"))
    assert alert is not None


def test_registry_all_stats() -> None:
    reg = BaselineRegistry()
    reg.observe("a", _make_action())
    reg.observe("b", _make_action())
    stats = reg.all_stats()
    assert "a" in stats
    assert "b" in stats


def test_alert_to_dict(baseline: AgentBaseline) -> None:
    for _ in range(AgentBaseline.LEARNING_THRESHOLD):
        baseline.observe(_make_action(tool="tool_a"))
    alert = baseline.check(_make_action(tool="tool_b"))
    assert alert is not None
    d = alert.to_dict()
    assert "anomaly_type" in d
    assert "agent_id" in d
    assert "action" in d
