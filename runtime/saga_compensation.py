#!/usr/bin/env python3
"""Saga compensation for multi-step transactions (from agent-governance-toolkit).

Automatic rollback for multi-step agent transactions. Each step has
a forward action and a compensation action. If any step fails, all
previously completed steps are compensated in reverse order.

This is a lightweight in-memory saga pattern, complementing the
durable ``runtime.saga.SagaOrchestrator`` which persists state to SQLite.

Usage::

    from runtime.saga_compensation import CompensationSaga

    saga = CompensationSaga()
    saga.add_step("create_user", forward=lambda: "user-1", compensate=lambda uid: None)
    saga.add_step("create_billing", forward=lambda: "bill-1", compensate=lambda bid: None)
    result = saga.execute()
    if not result.success:
        saga.compensate()
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CompensationStep:
    """A single step in a compensation saga."""

    name: str
    forward: Callable[[], Any]
    compensate: Callable[[Any], None] | None = None
    result: Any = None
    completed: bool = False


@dataclass
class CompensationResult:
    """Result of a compensation saga execution."""

    success: bool
    completed_steps: list[str] = field(default_factory=list)
    failed_step: str | None = None
    error: str = ""
    compensated: bool = False


@dataclass
class CompensationSaga:
    """Saga pattern for multi-step transactions with compensation.

    If any step fails, all previously completed steps are compensated
    in reverse order. This ensures atomicity across distributed operations.
    """

    steps: list[CompensationStep] = field(default_factory=list)
    _completed: list[CompensationStep] = field(default_factory=list)

    def add_step(
        self,
        name: str,
        forward: Callable[[], Any],
        compensate: Callable[[Any], None] | None = None,
    ) -> CompensationStep:
        """Add a step to the saga."""
        step = CompensationStep(name=name, forward=forward, compensate=compensate)
        self.steps.append(step)
        return step

    def execute(self) -> CompensationResult:
        """Execute all steps in order. Compensates on failure."""
        for step in self.steps:
            try:
                step.result = step.forward()
                step.completed = True
                self._completed.append(step)
            except Exception as e:
                return CompensationResult(
                    success=False,
                    completed_steps=[s.name for s in self._completed],
                    failed_step=step.name,
                    error=str(e),
                )
        return CompensationResult(
            success=True,
            completed_steps=[s.name for s in self._completed],
        )

    def compensate(self) -> CompensationResult:
        """Compensate all completed steps in reverse order."""
        for step in reversed(self._completed):
            if step.compensate:
                with contextlib.suppress(Exception):
                    step.compensate(step.result)
            step.completed = False
        compensated_names = [s.name for s in self._completed]
        self._completed.clear()
        return CompensationResult(
            success=False,
            compensated=True,
            completed_steps=compensated_names,
        )


if __name__ == "__main__":
    saga = CompensationSaga()
    saga.add_step("step1", forward=lambda: "r1", compensate=lambda r: print(f"Undo {r}"))
    saga.add_step("step2", forward=lambda: "r2", compensate=lambda r: print(f"Undo {r}"))
    saga.add_step("step3", forward=lambda: (_ for _ in ()).throw(ValueError("fail")),
                   compensate=lambda r: print(f"Undo {r}"))
    result = saga.execute()
    print(f"Success: {result.success}, Failed at: {result.failed_step}")
    if not result.success:
        saga.compensate()
