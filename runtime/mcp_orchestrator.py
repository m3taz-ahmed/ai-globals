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
                    # Substitute whenever the step ran (even falsy outputs
                    # like 0/""/[]/{}/False); only a missing result or a
                    # missing attribute keeps the literal placeholder.
                    if result is not None and result.status == StepStatus.COMPLETED:
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
            # Log the full traceback; return only the message (no stack
            # leak to callers).
            _logger.warning("orchestrator step %s failed: %s", step.id, exc)
            return StepResult(step_id=step.id, status=StepStatus.FAILED, error=str(exc))

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

    def _ready_steps(self, plan: Plan) -> list[Step]:
        completed = {r.step_id for r in self._results.values() if r.status == StepStatus.COMPLETED}
        return [s for s in plan.steps if s.id not in self._results and all(dep in completed for dep in s.depends_on)]

    def _unsatisfiable(self, plan: Plan) -> list[str]:
        """Return step ids whose dependencies can never be satisfied."""
        known = {s.id for s in plan.steps}
        return [s.id for s in plan.steps if any(dep not in known for dep in s.depends_on)]

    async def execute(self, plan: Plan, parallel: bool = False) -> dict[str, StepResult]:
        """Execute a plan. Supports parallel execution of independent steps."""
        return await self._execute_async(plan, parallel=parallel)

    async def execute_async(self, plan: Plan, parallel: bool = False) -> dict[str, StepResult]:
        """Async alias for :meth:`execute` (same coroutine)."""
        return await self._execute_async(plan, parallel=parallel)

    async def _execute_async(self, plan: Plan, parallel: bool = False) -> dict[str, StepResult]:
        """Execute a plan. Supports parallel execution of independent steps."""
        self._results = {}
        pending = {s.id for s in plan.steps}
        blocked = self._unsatisfiable(plan)
        if blocked:
            for step_id in blocked:
                self._results[step_id] = StepResult(
                    step_id=step_id, status=StepStatus.FAILED,
                    error=f"unsatisfiable dependencies for step {step_id!r}",
                )
                pending.discard(step_id)

        while pending:
            ready = self._ready_steps(plan)
            if not ready:
                # Deadlock (failed deps): mark the remainder failed loudly
                # instead of returning a silent partial result.
                for step in plan.steps:
                    if step.id in pending:
                        self._results[step.id] = StepResult(
                            step_id=step.id, status=StepStatus.FAILED,
                            error="step never became ready (a dependency failed or is missing)",
                        )
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
                    # Roll back only the dependency ancestors of the failed
                    # step (not unrelated parallel branches).
                    for step in self._failed_chain(plan, result.step_id):
                        step_result = self._results.get(step.id)
                        if step.rollback_tool and step_result is not None and step_result.status == StepStatus.COMPLETED:
                            self._results[step.id] = await self._rollback_step(step)
                    return self._results

        return self._results

    def _failed_chain(self, plan: Plan, failed_id: str) -> list[Step]:
        """Completed steps that the failed step (transitively) depends on."""
        by_id = {s.id: s for s in plan.steps}
        chain: list[Step] = []
        visiting = [failed_id]
        seen = {failed_id}
        ancestors: set[str] = set()
        while visiting:
            current = visiting.pop()
            step = by_id.get(current)
            if step is None:
                continue
            for dep in step.depends_on:
                if dep not in seen:
                    seen.add(dep)
                    ancestors.add(dep)
                    visiting.append(dep)
        for step in reversed(plan.steps):
            if step.id in ancestors:
                chain.append(step)
        return chain


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
