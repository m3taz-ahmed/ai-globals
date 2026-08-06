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
        from aios_mcp.agent import ToolCall

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
            from aios_mcp.agent import ToolCall

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
