#!/usr/bin/env python3
"""Tests for runtime.mcp_orchestrator."""

from __future__ import annotations

import asyncio
from typing import Any

from runtime.mcp_orchestrator import McpOrchestrator, Plan, Step, StepStatus


class _FakeAgent:
    def __init__(self, outputs: dict[str, Any] | None = None) -> None:
        self.outputs = outputs or {}

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> object:
        from aizee_mcp.agent import ToolCall

        return ToolCall(tool=name, arguments=arguments, result=self.outputs.get(name, arguments))


def test_plan_builds():
    plan = Plan(
        id="test",
        steps=[
            Step(id="a", tool="read", arguments={"path": "x"}),
            Step(id="b", tool="write", arguments={"content": "${a.result}"}, depends_on=["a"]),
        ],
    )
    assert plan.steps[1].depends_on == ["a"]


def test_sequential_execution():
    agent = _FakeAgent({"read": {"content": "hello"}, "write": {"ok": True}})
    orch = McpOrchestrator(agent)
    plan = Plan(
        id="seq",
        steps=[
            Step(id="a", tool="read", arguments={"path": "x"}),
            Step(id="b", tool="write", arguments={"content": "${a.output.content}"}, depends_on=["a"]),
        ],
    )
    results = asyncio.run(orch.execute(plan))
    assert results["a"].status == StepStatus.COMPLETED
    assert results["b"].status == StepStatus.COMPLETED
    assert results["b"].output == {"ok": True}


def test_rollback():
    class FailAgent:
        async def call_tool(self, name: str, arguments: dict[str, Any]) -> object:
            from aizee_mcp.agent import ToolCall

            if name == "write":
                return ToolCall(tool=name, arguments=arguments, error="disk full")
            return ToolCall(tool=name, arguments=arguments, result={"ok": True})

    orch = McpOrchestrator(FailAgent())
    plan = Plan(
        id="rollback",
        steps=[
            Step(id="a", tool="read", arguments={}, rollback_tool="undo"),
            Step(id="b", tool="write", arguments={}, depends_on=["a"]),
        ],
    )
    results = asyncio.run(orch.execute(plan))
    assert results["a"].status == StepStatus.ROLLED_BACK
    assert results["b"].status == StepStatus.FAILED


def test_run_step_exception():
    """Lines 93-94: _run_step catches exceptions and returns FAILED with traceback."""
    class CrashAgent:
        async def call_tool(self, name: str, arguments: dict[str, Any]) -> object:
            raise RuntimeError("agent crashed")

    orch = McpOrchestrator(CrashAgent())
    plan = Plan(id="crash", steps=[Step(id="a", tool="read", arguments={})])
    results = asyncio.run(orch.execute(plan))
    assert results["a"].status == StepStatus.FAILED
    assert "agent crashed" in results["a"].error
    assert "Traceback" in results["a"].error


def test_rollback_step_no_tool():
    """Line 98: _rollback_step with no rollback_tool returns ROLLED_BACK."""
    agent = _FakeAgent()
    orch = McpOrchestrator(agent)
    step = Step(id="a", tool="read", arguments={})  # no rollback_tool
    result = asyncio.run(orch._rollback_step(step))
    assert result.status == StepStatus.ROLLED_BACK
    assert result.rollback_output is None


def test_rollback_step_exception():
    """Lines 107-108: _rollback_step catches exceptions and returns ROLLED_BACK with error."""
    class CrashAgent:
        async def call_tool(self, name: str, arguments: dict[str, Any]) -> object:
            raise RuntimeError("rollback crashed")

    orch = McpOrchestrator(CrashAgent())
    step = Step(id="a", tool="read", arguments={}, rollback_tool="undo")
    result = asyncio.run(orch._rollback_step(step))
    assert result.status == StepStatus.ROLLED_BACK
    assert "rollback crashed" in result.rollback_error


def test_no_ready_steps_breaks():
    """Line 126: circular dependency causes no ready steps, loop breaks."""
    agent = _FakeAgent()
    orch = McpOrchestrator(agent)
    plan = Plan(
        id="circular",
        steps=[
            Step(id="a", tool="read", arguments={}, depends_on=["b"]),
            Step(id="b", tool="write", arguments={}, depends_on=["a"]),
        ],
    )
    results = asyncio.run(orch.execute(plan))
    # No steps can execute — both depend on each other
    assert len(results) == 0


def test_parallel_execution():
    """Lines 131-132: parallel execution via asyncio.gather."""
    agent = _FakeAgent({"read": {"content": "hello"}, "write": {"ok": True}})
    orch = McpOrchestrator(agent)
    plan = Plan(
        id="parallel",
        steps=[
            Step(id="a", tool="read", arguments={"path": "x"}),
            Step(id="b", tool="write", arguments={"path": "y"}),
        ],
    )
    results = asyncio.run(orch.execute(plan, parallel=True))
    assert results["a"].status == StepStatus.COMPLETED
    assert results["b"].status == StepStatus.COMPLETED


def test_deep_get_list_index():
    """Line 157: _deep_get with list and numeric index."""
    from runtime.mcp_orchestrator import _deep_get

    obj = {"items": ["first", "second", "third"]}
    assert _deep_get(obj, "items.0") == "first"
    assert _deep_get(obj, "items.2") == "third"


def test_deep_get_list_out_of_range():
    """Line 157: _deep_get with list index out of range returns None."""
    from runtime.mcp_orchestrator import _deep_get

    obj = {"items": ["first"]}
    assert _deep_get(obj, "items.5") is None


def test_deep_get_unsupported_type():
    """Line 160: _deep_get with unsupported type returns None."""
    from runtime.mcp_orchestrator import _deep_get

    obj = "just a string"
    assert _deep_get(obj, "some.attr") is None
