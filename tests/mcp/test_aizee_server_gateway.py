"""Coverage tests for aizee_server agent-gateway wrapper paths (P0.1)."""
from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

import aizee_mcp.aizee_server as srv
from runtime.agent_gateway import Verdict

pytestmark = pytest.mark.mcp


# --- _gateway_pre_check ----------------------------------------------------


def test_pre_check_kernel_unavailable_degrades():
    with patch.object(srv, "kernel", side_effect=RuntimeError("no kernel")):
        assert srv._gateway_pre_check("t", {}) is None


def test_pre_check_gateway_error_degrades():
    k = SimpleNamespace(
        agent_gateway=SimpleNamespace(check_request=lambda ctx: (_ for _ in ()).throw(RuntimeError("x")))
    )
    with patch.object(srv, "kernel", return_value=k):
        assert srv._gateway_pre_check("t", {}) is None


def test_pre_check_block_returns_error_json():
    blk = SimpleNamespace(verdict=Verdict.BLOCK, reason="injection")
    k = SimpleNamespace(
        agent_gateway=SimpleNamespace(check_request=lambda ctx: (Verdict.BLOCK, [blk]))
    )
    with patch.object(srv, "kernel", return_value=k):
        out = srv._gateway_pre_check("t", {"x": 1})
    assert out is not None
    assert json.loads(out)["gate"] == "agent_gateway"
    assert "injection" in out


def test_pre_check_block_no_blocking_result_falls_back():
    other = SimpleNamespace(verdict=Verdict.ALLOW, reason="ok")
    k = SimpleNamespace(
        agent_gateway=SimpleNamespace(check_request=lambda ctx: (Verdict.BLOCK, [other]))
    )
    with patch.object(srv, "kernel", return_value=k):
        out = srv._gateway_pre_check("t", {})
    assert out is not None and "blocked" in out


def test_pre_check_allow_passes():
    k = SimpleNamespace(
        agent_gateway=SimpleNamespace(check_request=lambda ctx: (Verdict.ALLOW, []))
    )
    with patch.object(srv, "kernel", return_value=k):
        assert srv._gateway_pre_check("t", {}) is None


# --- _gateway_post_check ---------------------------------------------------


def test_post_check_none_result():
    assert srv._gateway_post_check("t", None) is None


def test_post_check_unserializable_result():
    class Unserializable:
        def __str__(self) -> str:
            raise TypeError("nope")

        __repr__ = __str__

    obj = Unserializable()
    assert srv._gateway_post_check("t", obj) is obj


def test_post_check_kernel_error_returns_result():
    with patch.object(srv, "kernel", side_effect=RuntimeError("x")):
        assert srv._gateway_post_check("t", "fine") == "fine"


def test_post_check_blocked_result():
    k = SimpleNamespace(check_tool_result=lambda s, n, t: (False, "secret"))
    with patch.object(srv, "kernel", return_value=k):
        out = srv._gateway_post_check("t", "leak: AKIA...")
    assert json.loads(out)["gate"] == "agent_gateway"


def test_post_check_redacted_str_result():
    k = SimpleNamespace(check_tool_result=lambda s, n, t: (True, "[REDACTED]"))
    with patch.object(srv, "kernel", return_value=k):
        assert srv._gateway_post_check("t", "secret") == "[REDACTED]"


def test_post_check_redacted_non_str_result_unchanged():
    k = SimpleNamespace(check_tool_result=lambda s, n, t: (True, "{}"))
    with patch.object(srv, "kernel", return_value=k):
        assert srv._gateway_post_check("t", {"a": 1}) == {"a": 1}


# --- _wrap_tool_with_rbac --------------------------------------------------


def _fake_tool(fn, name="mytool"):
    return SimpleNamespace(name=name, fn=fn, is_async=asyncio.iscoroutinefunction(fn))


def test_wrap_sync_rbac_exception_denies():
    tool = _fake_tool(lambda **kw: "ran", name="t_sync_err")
    srv._wrap_tool_with_rbac(tool)
    with patch.object(srv, "check_tool_permission", side_effect=RuntimeError("rbac boom")):
        out = tool.fn()
    assert json.loads(out)["ok"] is False


def test_wrap_async_rbac_exception_denies():
    async def fn(**kw):
        return "ran"

    tool = _fake_tool(fn, name="t_async_err")
    srv._wrap_tool_with_rbac(tool)
    with patch.object(srv, "check_tool_permission", side_effect=RuntimeError("rbac boom")):
        out = asyncio.run(tool.fn())
    assert json.loads(out)["ok"] is False


def test_wrap_sync_gate_error_returned():
    tool = _fake_tool(lambda **kw: "should-not-run", name="t_sync_gate")
    srv._wrap_tool_with_rbac(tool)
    with (
        patch.object(srv, "check_tool_permission", return_value=True),
        patch.object(srv, "_gateway_pre_check", return_value='{"ok": false}'),
    ):
        assert tool.fn() == '{"ok": false}'


def test_wrap_async_gate_error_returned():
    async def fn(**kw):
        return "should-not-run"

    tool = _fake_tool(fn, name="t_async_gate")
    srv._wrap_tool_with_rbac(tool)
    with (
        patch.object(srv, "check_tool_permission", return_value=True),
        patch.object(srv, "_gateway_pre_check", return_value='{"ok": false}'),
    ):
        assert asyncio.run(tool.fn()) == '{"ok": false}'


def test_wrap_sync_full_allow_path():
    tool = _fake_tool(lambda **kw: "ran-ok", name="t_sync_ok")
    srv._wrap_tool_with_rbac(tool)
    with (
        patch.object(srv, "check_tool_permission", return_value=True),
        patch.object(srv, "_gateway_pre_check", return_value=None),
        patch.object(srv, "_gateway_post_check", side_effect=lambda n, r: r),
    ):
        assert tool.fn() == "ran-ok"


def test_wrap_idempotent_via_guarded_names():
    tool = _fake_tool(lambda **kw: "x", name="t_idem")
    srv._wrap_tool_with_rbac(tool)
    first = tool.fn
    srv._wrap_tool_with_rbac(tool)  # already guarded -> no double wrap
    assert tool.fn is first
