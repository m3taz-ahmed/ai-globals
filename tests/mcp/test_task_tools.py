"""Tests for aizee_mcp/tools/task_tools.py MCP tools."""

from __future__ import annotations

import json
from typing import Any

import pytest

from aizee_mcp.tools.task_tools import register_task_tools  # pyright: ignore[reportMissingImports]

pytestmark = pytest.mark.mcp


class _FakeTool:
    def __call__(self, fn: Any | None = None) -> Any:
        if fn is not None:
            _captured_tools[fn.__name__] = fn
            return fn

        def decorator(inner_fn: Any) -> Any:
            _captured_tools[inner_fn.__name__] = inner_fn
            return inner_fn

        return decorator


class _FakeMCP:
    def __init__(self) -> None:
        self.tool = _FakeTool()


_captured_tools: dict[str, Any] = {}


def _register() -> None:
    _captured_tools.clear()
    register_task_tools(_FakeMCP())


def _parse(result: str) -> dict[str, Any]:
    return json.loads(result)


def test_all_task_tools_registered() -> None:
    _register()
    expected = {
        "task_classify", "task_decompose", "task_status", "task_start",
        "task_verify", "task_complete", "task_block", "task_finish",
        "task_abandon", "task_scope",
    }
    assert expected <= set(_captured_tools)


def test_classify_heuristic_no_kernel() -> None:
    _register()
    out = _parse(_captured_tools["task_classify"](prompt="fix typo in readme"))
    assert out["ok"] is True
    assert out["result"]["heuristic"]["level"] in {"trivial", "standard", "complex"}


def test_task_error_returns_json_not_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    _register()
    import aizee_mcp.tools.task_tools as mod

    class _Boom:
        def start(self, task_id: str) -> Any:
            raise ValueError("no active plan")

    monkeypatch.setattr(mod, "_mgr", lambda: _Boom())
    out = _parse(_captured_tools["task_start"](task_id="x"))
    assert out["ok"] is False and "no active plan" in out["error"]
