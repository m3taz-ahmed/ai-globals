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


class _FakePlan:
    def to_dict(self) -> dict[str, Any]:
        return {"tasks": ["a"]}

    def next_pending(self) -> None:
        return None


class _FakeMgr:
    """Stand-in task-contract manager returning canned results."""

    def record_classification(self, prompt: str, level: str, reason: str) -> dict[str, Any]:
        return {"level": level, "reason": reason}

    def decompose(self, *a: Any) -> _FakePlan:
        return _FakePlan()

    def status(self) -> dict[str, Any]:
        return {"status": "active"}

    def start(self, task_id: str) -> dict[str, Any]:
        return {"started": task_id}

    def verify(self, task_id: str, evidence: str, run_cmd: bool = False) -> dict[str, Any]:
        return {"verified": task_id, "cmd": run_cmd}

    def complete(self, task_id: str, note: str = "") -> dict[str, Any]:
        return {"done": task_id}

    def block(self, task_id: str, reason: str) -> dict[str, Any]:
        return {"blocked": task_id, "reason": reason}

    def finish(self, note: str = "") -> dict[str, Any]:
        return {"closed": True, "note": note}

    def abandon(self, reason: str) -> dict[str, Any]:
        return {"abandoned": True, "reason": reason}

    def scope_check(self, path: str) -> dict[str, Any]:
        return {"allowed": True, "path": path}


def test_all_tools_success_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    _register()
    import aizee_mcp.tools.task_tools as mod

    monkeypatch.setattr(mod, "_mgr", _FakeMgr)
    calls = {
        "task_classify": {"prompt": "p", "level": "standard", "reason": "r"},
        "task_decompose": {"title": "t", "prompt": "p", "tasks": [],
                         "classification": "standard", "reason": "r"},
        "task_status": {},
        "task_start": {"task_id": "a"},
        "task_verify": {"task_id": "a", "evidence": "e", "run_cmd": True},
        "task_complete": {"task_id": "a", "note": "n"},
        "task_block": {"task_id": "a", "reason": "r"},
        "task_finish": {"note": "done"},
        "task_abandon": {"reason": "gave up"},
        "task_scope": {"path": "src/x.py"},
    }
    for name, kwargs in calls.items():
        out = _parse(_captured_tools[name](**kwargs))
        assert out["ok"] is True, name
    # decompose wraps the plan object + next pointer
    assert _parse(_captured_tools["task_decompose"](**calls["task_decompose"]))[
        "result"]["plan"]["tasks"] == ["a"]


def test_each_tool_error_path(monkeypatch: pytest.MonkeyPatch) -> None:
    _register()
    import aizee_mcp.tools.task_tools as mod

    class _BoomMgr:
        def __getattr__(self, name: str) -> Any:
            def _raise(*a: Any, **k: Any) -> Any:
                raise ValueError(f"{name} blew up")
            return _raise

    monkeypatch.setattr(mod, "_mgr", _BoomMgr)
    calls = {
        "task_classify": {"prompt": "p", "level": "x", "reason": "r"},
        "task_decompose": {"title": "t", "prompt": "p", "tasks": [],
                           "classification": "s", "reason": "r"},
        "task_status": {},
        "task_start": {"task_id": "a"},
        "task_verify": {"task_id": "a", "evidence": "e", "run_cmd": False},
        "task_complete": {"task_id": "a", "note": "n"},
        "task_block": {"task_id": "a", "reason": "r"},
        "task_finish": {"note": "n"},
        "task_abandon": {"reason": "r"},
        "task_scope": {"path": "p"},
    }
    for name, kwargs in calls.items():
        out = _parse(_captured_tools[name](**kwargs))
        assert out["ok"] is False, name
        assert "blew up" in out["error"]


def test_mgr_uses_kernel_task_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    import types

    import aizee_mcp.tools.task_tools as mod

    sentinel = object()
    monkeypatch.setattr(mod, "kernel",
                        lambda: types.SimpleNamespace(task_contract=sentinel))
    assert mod._mgr() is sentinel
