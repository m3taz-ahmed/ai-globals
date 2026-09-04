#!/usr/bin/env python3
"""Governance hooks for aiZee.

Re-implements the agent-governance-toolkit pattern: decorator-style hooks that
wrap actions with audit, telemetry, policy, and tracing checks.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

from runtime.audit import AuditLogger
from runtime.telemetry import TelemetryCollector

_logger = logging.getLogger(__name__)


class GovernanceHooks:
    """Container for governance hook implementations."""

    def __init__(self, audit: AuditLogger, telemetry: TelemetryCollector) -> None:
        self.audit = audit
        self.telemetry = telemetry

    @contextmanager
    def around_action(self, action: str, *args: Any, **kwargs: Any) -> Iterator[None]:
        """Context manager that audits and records telemetry around an action."""
        redacted_kwargs: Any = kwargs
        redactor = getattr(self.audit, "_redact", None)
        if callable(redactor):
            try:
                redacted_kwargs = redactor(kwargs)
            except Exception:
                redacted_kwargs = kwargs
        redacted_args: Any = args
        if callable(redactor) and args:
            try:
                redacted_args = redactor(list(args))
            except Exception:
                redacted_args = args
        self.audit.log(action, {"args": redacted_args, "kwargs": redacted_kwargs})
        try:
            yield None
        except Exception as exc:
            _logger.debug("governance action %s failed: %s", action, exc, exc_info=True)
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
                metadata={"args": redacted_args, "kwargs": redacted_kwargs},
            )

    def wrap(self, action: str, fn: Callable[..., Any]) -> Callable[..., Any]:
        """Wrap a function with governance hooks."""

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with self.around_action(action, *args, **kwargs):
                return fn(*args, **kwargs)

        return wrapper
