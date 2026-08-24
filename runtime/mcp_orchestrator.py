#!/usr/bin/env python3
"""MCP orchestration layer for multi-step agent plans.

Re-implements patterns from mcp-orchestrator and shackleai/orchestrator:
- declarative step plans
- sequential / parallel execution
- rollback on failure
- artifact passing between steps
"""

from __future__ import annotations

import asyncio
import logging
import traceback
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from aizee_mcp.agent import McpAgent

_logger = logging.getLogger(__name__)


class StepStatus(str, Enum):
    """Status of a plan step."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class Step:
    """A single step in an orchestrated plan."""

    id: str
    tool: str
    arguments: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    rollback_tool: str | None = None
    rollback_arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class StepResult:
    """Result of executing a step."""

    step_id: str
    status: StepStatus
    output: Any = None
    error: str = ""
    rollback_output: Any = None
    rollback_error: str = ""


@dataclass
class Plan:
    """A multi-step plan."""

    id: str
    steps: list[Step]


class McpOrchestrator:
    """Orchestrate multi-step plans across MCP tools."""

    def __init__(self, agent: McpAgent) -> None:
        self.agent = agent
        self._results: dict[str, StepResult] = {}

    def _resolve_arguments(self, step: Step) -> dict[str, Any]:
        """Replace references like ``${step_id.output}`` with prior results."""
        resolved: dict[str, Any] = {}
        for key, value in step.arguments.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                ref = value[2:-1]
                if "." in ref:
                    step_id, attr = ref.split(".", 1)
                    result = self._results.get(step_id)
                    if result and result.output:
                        resolved[key] = _deep_get(result.output, attr)
                        continue
            resolved[key] = value
        return resolved

    async def _run_step(self, step: Step) -> StepResult:
        args = self._resolve_arguments(step)
        try:
            call = await self.agent.call_tool(step.tool, args)
            if call.error:
                return StepResult(step_id=step.id, status=StepStatus.FAILED, error=call.error)
            return StepResult(step_id=step.id, status=StepStatus.COMPLETED, output=call.result)
        except Exception as exc:
            _logger.debug("orchestrator step failed: %s", exc, exc_info=True)
            return StepResult(step_id=step.id, status=StepStatus.FAILED, error=f"{exc!s}\n{traceback.format_exc()}")

    async def _rollback_step(self, step: Step) -> StepResult:
        if not step.rollback_tool:
            return StepResult(step_id=step.id, status=StepStatus.ROLLED_BACK)
        try:
            call = await self.agent.call_tool(step.rollback_tool, step.rollback_arguments)
            return StepResult(
                step_id=step.id,
                status=StepStatus.ROLLED_BACK,
                rollback_output=call.result,
                rollback_error=call.error,
            )
        except Exception as exc:
            _logger.debug("orchestrator rollback failed: %s", exc, exc_info=True)
            return StepResult(
                step_id=step.id,
                status=StepStatus.ROLLED_BACK,
                rollback_error=f"{exc!s}",
            )

    async def _ready_steps(self, plan: Plan) -> list[Step]:
        completed = {r.step_id for r in self._results.values() if r.status == StepStatus.COMPLETED}
        return [s for s in plan.steps if s.id not in self._results and all(dep in completed for dep in s.depends_on)]

    async def execute(self, plan: Plan, parallel: bool = False) -> dict[str, StepResult]:
        """Execute a plan. Supports parallel execution of independent steps."""
        self._results = {}
        pending = {s.id for s in plan.steps}

        while pending:
            ready = await self._ready_steps(plan)
            if not ready:
                break
            for step in ready:
                pending.discard(step.id)

            if parallel:
                coros = [self._run_step(step) for step in ready]
                results = await asyncio.gather(*coros)
            else:
                results = []
                for step in ready:
                    results.append(await self._run_step(step))

            for result in results:
                self._results[result.step_id] = result
                if result.status == StepStatus.FAILED:
                    for step in reversed(plan.steps):
                        step_result = self._results.get(step.id)
                        if step.rollback_tool and step_result is not None and step_result.status == StepStatus.COMPLETED:
                            self._results[step.id] = await self._rollback_step(step)
                    return self._results

        return self._results


def _deep_get(obj: Any, attr: str) -> Any:
    """Get a dotted attribute from a dict/list."""
    parts = attr.split(".")
    value = obj
    for part in parts:
        if isinstance(value, dict):
            value = value.get(part)
        elif isinstance(value, list) and part.isdigit():
            value = value[int(part)] if int(part) < len(value) else None
        else:
            return None
    return value
