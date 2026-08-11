#!/usr/bin/env python3
"""Governance hooks for AI Global OS.

Re-implements the agent-governance-toolkit pattern: decorator-style hooks that
wrap actions with audit, telemetry, policy, and tracing checks.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

from runtime.audit import AuditLogger
from runtime.telemetry import TelemetryCollector


class GovernanceHooks:
    """Container for governance hook implementations."""

    def __init__(self, audit: AuditLogger, telemetry: TelemetryCollector) -> None:
        self.audit = audit
        self.telemetry = telemetry

    @contextmanager
    def around_action(self, action: str, **kwargs: Any) -> Iterator[GovernanceHooks]:
        """Context manager that audits and records telemetry around an action."""
        self.audit.log(action, kwargs)
        try:
            yield self
        except Exception as exc:
            self.telemetry.record(
                event_type="action",
                action=action,
                status="failed",
                metadata={"error": f"{exc!s}"},
            )
            raise
        else:
            self.telemetry.record(
                event_type="action",
                action=action,
                status="completed",
                metadata=kwargs,
            )

    def wrap(self, action: str, fn: Callable[..., Any]) -> Callable[..., Any]:
        """Wrap a function with governance hooks."""

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with self.around_action(action, **kwargs):
                return fn(*args, **kwargs)

        return wrapper
