"""Command object pattern — decompose complex service workflows into discrete, testable commands.

Inspired by Invoice Ninja's `new MarkPaid()` / `new ApplyNumber()` pattern where each
operation delegates to a dedicated command class, providing better testability and
single responsibility than monolithic service methods.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from runtime.schemas import AizeeError, ErrorSeverity

_logger = logging.getLogger(__name__)


class CommandStatus(str, Enum):
    """Lifecycle status of a command execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class CommandError(AizeeError):
    """Raised when a command execution fails."""

    def __init__(self, command_name: str, message: str, context: dict[str, Any] | None = None) -> None:
        super().__init__(
            "COMMAND_ERROR",
            f"Command '{command_name}' failed: {message}",
            ErrorSeverity.HIGH,
            {"command_name": command_name, **(context or {})},
        )


@dataclass
class CommandResult:
    """Outcome of a command execution."""

    status: CommandStatus
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    @property
    def is_success(self) -> bool:
        """True if the command completed successfully."""
        return self.status is CommandStatus.COMPLETED

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for logging/API responses."""
        result: dict[str, Any] = {"status": self.status.value, "data": dict(self.data)}
        if self.error is not None:
            result["error"] = self.error
        return result


class Command(ABC):
    """Base interface for discrete workflow commands.

    Each command encapsulates a single operation with a clear contract:
    - ``name``: identifier for audit/logging
    - ``execute``: the operation, returns a CommandResult
    - ``rollback``: optional compensation (Saga-style)
    """

    name: str = ""

    @abstractmethod
    def execute(self, context: dict[str, Any]) -> CommandResult:
        """Run the command against the given context. Must not mutate context destructively."""

    def rollback(self, context: dict[str, Any]) -> CommandResult:
        """Compensating action. Default: no-op (not all commands are compensable)."""
        return CommandResult(status=CommandStatus.SKIPPED, data={"reason": "no rollback defined"})

    def __repr__(self) -> str:
        return f"<Command {self.name or self.__class__.__name__}>"


class CommandBus:
    """Execute a sequence of commands with optional rollback on failure (Saga pattern).

    Commands run in order. If one fails and ``rollback_on_failure`` is True,
    all previously-completed commands are rolled back in reverse order.
    """

    def __init__(self, commands: list[Command] | None = None, *, rollback_on_failure: bool = True) -> None:
        self._commands: list[Command] = list(commands or [])
        self._rollback_on_failure = rollback_on_failure

    def add(self, command: Command) -> CommandBus:
        """Append a command to the bus. Returns self for chaining."""
        self._commands.append(command)
        return self

    def execute(self, context: dict[str, Any] | None = None) -> list[CommandResult]:
        """Execute all commands in order. On failure, optionally rollback completed commands."""
        ctx = dict(context or {})
        results: list[CommandResult] = []
        completed: list[tuple[int, Command]] = []

        for idx, cmd in enumerate(self._commands):
            try:
                result = cmd.execute(ctx)
            except CommandError:
                raise
            except Exception as exc:
                _logger.debug("command execution failed: %s", exc, exc_info=True)
                raise CommandError(cmd.name or cmd.__class__.__name__, str(exc)) from exc

            results.append(result)
            if result.is_success:
                completed.append((idx, cmd))
            elif self._rollback_on_failure:
                self._rollback_completed(completed, ctx, results)
                break

        return results

    def _rollback_completed(
        self,
        completed: list[tuple[int, Command]],
        ctx: dict[str, Any],
        results: list[CommandResult],
    ) -> None:
        """Rollback completed commands in reverse order."""
        for _, cmd in reversed(completed):
            try:
                rb = cmd.rollback(ctx)
                results.append(rb)
            except Exception as exc:
                _logger.debug("command rollback failed: %s", exc, exc_info=True)
                results.append(
                    CommandResult(status=CommandStatus.FAILED, error=f"rollback error: {exc}")
                )

    @property
    def commands(self) -> list[Command]:
        """Read-only view of registered commands."""
        return list(self._commands)
