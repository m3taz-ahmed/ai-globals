"""Tests for runtime/commands.py — Command object pattern + CommandBus."""
from __future__ import annotations

import pytest

from runtime.commands import Command, CommandBus, CommandError, CommandResult, CommandStatus


class _SuccessCmd(Command):
    name = "success"

    def execute(self, context: dict[str, object]) -> CommandResult:
        context["ran"] = True
        return CommandResult(status=CommandStatus.COMPLETED, data={"value": 42})

    def rollback(self, context: dict[str, object]) -> CommandResult:
        context["rolled_back"] = True
        return CommandResult(status=CommandStatus.COMPLETED, data={"rolled": True})


class _FailCmd(Command):
    name = "fail"

    def execute(self, context: dict[str, object]) -> CommandResult:
        return CommandResult(status=CommandStatus.FAILED, error="boom")


class _NoRollbackCmd(Command):
    name = "no_rollback"

    def execute(self, context: dict[str, object]) -> CommandResult:
        return CommandResult(status=CommandStatus.COMPLETED, data={"ok": True})


class _ExceptionCmd(Command):
    name = "exception"

    def execute(self, context: dict[str, object]) -> CommandResult:
        raise ValueError("unexpected")


class _RollbackErrorCmd(Command):
    name = "rollback_error"

    def execute(self, context: dict[str, object]) -> CommandResult:
        return CommandResult(status=CommandStatus.COMPLETED, data={"ok": True})

    def rollback(self, context: dict[str, object]) -> CommandResult:
        raise RuntimeError("rollback failed")


# --- CommandResult ---

def test_command_result_success() -> None:
    r = CommandResult(status=CommandStatus.COMPLETED, data={"x": 1})
    assert r.is_success is True
    assert r.to_dict() == {"status": "completed", "data": {"x": 1}}


def test_command_result_failed_with_error() -> None:
    r = CommandResult(status=CommandStatus.FAILED, error="boom")
    assert r.is_success is False
    assert r.to_dict() == {"status": "failed", "data": {}, "error": "boom"}


def test_command_result_skipped() -> None:
    r = CommandResult(status=CommandStatus.SKIPPED)
    assert r.is_success is False
    assert "error" not in r.to_dict()


# --- Command base ---

def test_command_default_rollback_is_skipped() -> None:
    cmd = _NoRollbackCmd()
    result = cmd.rollback({})
    assert result.status is CommandStatus.SKIPPED


def test_command_repr() -> None:
    cmd = _SuccessCmd()
    assert "success" in repr(cmd)


# --- CommandBus ---

def test_bus_execute_all_success() -> None:
    bus = CommandBus([_SuccessCmd(), _NoRollbackCmd()])
    results = bus.execute({})
    assert len(results) == 2
    assert all(r.is_success for r in results)


def test_bus_stops_on_failure_with_rollback() -> None:
    bus = CommandBus([_SuccessCmd(), _FailCmd(), _NoRollbackCmd()], rollback_on_failure=True)
    results = bus.execute({})
    # success + fail + rollback of success = 3 results
    assert len(results) == 3
    assert results[0].is_success
    assert results[1].status is CommandStatus.FAILED
    assert results[2].is_success  # rollback result
    assert results[2].data.get("rolled") is True


def test_bus_no_rollback_on_failure() -> None:
    bus = CommandBus([_SuccessCmd(), _FailCmd()], rollback_on_failure=False)
    ctx: dict[str, object] = {}
    results = bus.execute(ctx)
    assert len(results) == 2
    assert "rolled_back" not in ctx


def test_bus_wraps_exception_into_command_error() -> None:
    bus = CommandBus([_ExceptionCmd()])
    with pytest.raises(CommandError) as exc_info:
        bus.execute({})
    assert "exception" in str(exc_info.value)


def test_bus_rollback_error_is_captured_not_raised() -> None:
    bus = CommandBus([_RollbackErrorCmd(), _FailCmd()], rollback_on_failure=True)
    results = bus.execute({})
    # success + fail + rollback-error result
    assert len(results) == 3
    assert results[2].status is CommandStatus.FAILED
    assert "rollback error" in (results[2].error or "")


def test_bus_add_chaining() -> None:
    bus = CommandBus()
    ret = bus.add(_SuccessCmd())
    assert ret is bus
    assert len(bus.commands) == 1


def test_bus_empty_executes_nothing() -> None:
    bus = CommandBus()
    results = bus.execute({})
    assert results == []


def test_bus_commands_read_only() -> None:
    bus = CommandBus([_SuccessCmd()])
    cmds = bus.commands
    cmds.clear()
    # Original should be unaffected
    assert len(bus.commands) == 1
