"""Fine-grained hook lifecycle — granular request/action pipeline hooks.

Inspired by Fastify's lifecycle hooks (``onRequest``, ``preValidation``,
``preHandler``, ``onResponse``, ``onError``) which offer finer control than
a single middleware pipeline. Applied to aiZee's guardian/action pipeline.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from runtime.schemas import AizeeError, ErrorSeverity

_logger = logging.getLogger(__name__)


class HookPhase(str, Enum):
    """Ordered phases in the action lifecycle."""

    PRE_RECEIVE = "pre_receive"
    PRE_VALIDATION = "pre_validation"
    PRE_HANDLER = "pre_handler"
    POST_HANDLER = "post_handler"
    POST_RESPONSE = "post_response"
    ON_ERROR = "on_error"


# Ordered phases for normal (non-error) execution
_NORMAL_PHASES: tuple[HookPhase, ...] = (
    HookPhase.PRE_RECEIVE,
    HookPhase.PRE_VALIDATION,
    HookPhase.PRE_HANDLER,
    HookPhase.POST_HANDLER,
    HookPhase.POST_RESPONSE,
)


class HookError(AizeeError):
    """Raised when a hook execution fails."""

    def __init__(self, phase: str, message: str, context: dict[str, Any] | None = None) -> None:
        super().__init__(
            "HOOK_ERROR",
            f"Hook in phase '{phase}' failed: {message}",
            ErrorSeverity.MEDIUM,
            {"phase": phase, **(context or {})},
        )


@dataclass
class HookContext:
    """Context passed through the hook lifecycle."""

    action: str
    attributes: dict[str, Any] = field(default_factory=dict)
    results: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    stopped: bool = False

    def stop(self) -> None:
        """Mark the lifecycle as stopped — no further phases run."""
        self.stopped = True

    def add_result(self, key: str, value: Any) -> None:
        """Store a result from a hook for downstream use."""
        self.results[key] = value

    def add_error(self, message: str) -> None:
        """Record a non-fatal error during hook execution."""
        self.errors.append(message)


HookCallable = Callable[[HookContext], None]


class HookRegistry:
    """Registry of hooks per phase with ordered execution.

    Hooks within a phase run in registration order. If a hook calls
    ``context.stop()``, no further hooks in that phase or subsequent
    phases execute.
    """

    def __init__(self) -> None:
        self._hooks: dict[HookPhase, list[HookCallable]] = {phase: [] for phase in HookPhase}

    def register(self, phase: HookPhase, hook: HookCallable) -> HookRegistry:
        """Register a hook for a phase. Returns self for chaining."""
        self._hooks[phase].append(hook)
        return self

    def on(self, phase: HookPhase) -> Callable[[HookCallable], HookCallable]:
        """Decorator to register a hook for a phase."""

        def decorator(fn: HookCallable) -> HookCallable:
            self.register(phase, fn)
            return fn

        return decorator

    def run_phase(self, phase: HookPhase, context: HookContext) -> None:
        """Run all hooks for a phase. Stops if context.stopped is set."""
        for hook in self._hooks[phase]:
            if context.stopped:
                return
            try:
                hook(context)
            except HookError:
                raise
            except Exception as exc:
                _logger.debug("hook phase %s failed: %s", phase.value, exc, exc_info=True)
                raise HookError(phase.value, str(exc)) from exc

    def run_lifecycle(self, action: str, attributes: dict[str, Any] | None = None) -> HookContext:
        """Run the full normal lifecycle (pre_receive → post_response)."""
        ctx = HookContext(action=action, attributes=dict(attributes or {}))
        for phase in _NORMAL_PHASES:
            if ctx.stopped:
                break
            self.run_phase(phase, ctx)
        return ctx

    def run_error(self, context: HookContext, error: Exception) -> None:
        """Run the ON_ERROR phase with the error recorded in context.

        If an ON_ERROR hook raises, the new error is chained from the
        original (``raise ... from original``) so neither is discarded;
        both are kept in ``context.errors``.
        """
        context.add_error(f"{type(error).__name__}: {error}")
        try:
            self.run_phase(HookPhase.ON_ERROR, context)
        except Exception as hook_exc:
            context.add_error(f"{type(hook_exc).__name__}: {hook_exc}")
            _logger.debug(
                "ON_ERROR hook failed while handling %s: %s",
                type(error).__name__, hook_exc, exc_info=True,
            )
            raise HookError(
                HookPhase.ON_ERROR.value,
                f"ON_ERROR handler failed ({hook_exc}) while handling original {type(error).__name__}: {error}",
            ) from error

    def hooks_for(self, phase: HookPhase) -> list[HookCallable]:
        """List hooks registered for a phase (read-only copy)."""
        return list(self._hooks[phase])

    def clear(self) -> None:
        """Remove all hooks from all phases."""
        for phase in HookPhase:
            self._hooks[phase].clear()
