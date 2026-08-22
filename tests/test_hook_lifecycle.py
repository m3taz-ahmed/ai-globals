"""Tests for runtime/hook_lifecycle.py — HookRegistry + HookPhase."""
from __future__ import annotations

import pytest

from runtime.hook_lifecycle import HookContext, HookError, HookPhase, HookRegistry


def test_hook_phases_ordered() -> None:
    phases = list(HookPhase)
    assert phases[0] is HookPhase.PRE_RECEIVE
    assert phases[-1] is HookPhase.ON_ERROR


def test_hook_context_stop_prevents_further_hooks() -> None:
    registry = HookRegistry()
    call_log: list[str] = []

    registry.on(HookPhase.PRE_RECEIVE)(lambda ctx: call_log.append("pre_receive"))
    registry.on(HookPhase.PRE_VALIDATION)(lambda ctx: (call_log.append("pre_validation"), ctx.stop()))
    registry.on(HookPhase.PRE_HANDLER)(lambda ctx: call_log.append("pre_handler"))
    registry.on(HookPhase.POST_HANDLER)(lambda ctx: call_log.append("post_handler"))

    ctx = registry.run_lifecycle("test_action")
    assert ctx.stopped is True
    assert call_log == ["pre_receive", "pre_validation"]


def test_hook_context_add_result_and_error() -> None:
    ctx = HookContext(action="test")
    ctx.add_result("key", "value")
    ctx.add_error("something went wrong")
    assert ctx.results == {"key": "value"}
    assert ctx.errors == ["something went wrong"]


def test_registry_run_full_lifecycle() -> None:
    registry = HookRegistry()
    call_log: list[str] = []

    for phase in HookPhase:
        if phase is not HookPhase.ON_ERROR:
            registry.register(phase, lambda ctx, p=phase: call_log.append(p.value))

    ctx = registry.run_lifecycle("test_action", {"attr": 1})
    assert ctx.stopped is False
    assert len(call_log) == 5  # 5 normal phases
    assert call_log[0] == "pre_receive"
    assert call_log[-1] == "post_response"


def test_registry_run_error_phase() -> None:
    registry = HookRegistry()
    error_log: list[str] = []

    registry.on(HookPhase.ON_ERROR)(lambda ctx: error_log.append(ctx.errors[0]))

    ctx = HookContext(action="test")
    registry.run_error(ctx, ValueError("test error"))
    assert len(error_log) == 1
    assert "ValueError" in error_log[0]


def test_registry_hook_exception_wrapped() -> None:
    registry = HookRegistry()

    def bad_hook(ctx: HookContext) -> None:
        raise ValueError("hook crashed")

    registry.register(HookPhase.PRE_RECEIVE, bad_hook)
    with pytest.raises(HookError) as exc_info:
        registry.run_lifecycle("test")
    assert "pre_receive" in str(exc_info.value)


def test_registry_hooks_for_returns_copy() -> None:
    registry = HookRegistry()
    h1 = lambda ctx: None  # noqa: E731
    registry.register(HookPhase.PRE_RECEIVE, h1)
    hooks = registry.hooks_for(HookPhase.PRE_RECEIVE)
    hooks.clear()
    assert len(registry.hooks_for(HookPhase.PRE_RECEIVE)) == 1


def test_registry_clear() -> None:
    registry = HookRegistry()
    registry.register(HookPhase.PRE_RECEIVE, lambda ctx: None)
    registry.clear()
    for phase in HookPhase:
        assert registry.hooks_for(phase) == []


def test_registry_decorator_returns_callable() -> None:
    registry = HookRegistry()

    @registry.on(HookPhase.POST_HANDLER)
    def my_hook(ctx: HookContext) -> None:
        ctx.add_result("ran", True)

    ctx = registry.run_lifecycle("test")
    assert ctx.results.get("ran") is True


def test_hook_context_default_attributes() -> None:
    ctx = HookContext(action="test")
    assert ctx.attributes == {}
    assert ctx.results == {}
    assert ctx.errors == []
    assert ctx.stopped is False
