"""Gap coverage for aizee_mcp/aizee_server.py internals."""

from __future__ import annotations

import json
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

import pytest

import aizee_mcp.aizee_server as srv


class TestAutoDiscover:
    def test_import_failure_skipped(self):
        info = SimpleNamespace(name="bad_tools")
        with patch("pkgutil.iter_modules", return_value=[info]), \
             patch("importlib.import_module", side_effect=ImportError("boom")):
            assert srv._auto_discover_tools() is False

    def test_non_tools_module_skipped(self):
        info = SimpleNamespace(name="common")
        with patch("pkgutil.iter_modules", return_value=[info]):
            assert srv._auto_discover_tools() is False

    def test_register_alias_preferred(self):
        mod = ModuleType("x_tools")
        called = []
        mod.register = lambda m: called.append(m)  # type: ignore[attr-defined]
        info = SimpleNamespace(name="x_tools")
        with patch("pkgutil.iter_modules", return_value=[info]), \
             patch("importlib.import_module", return_value=mod):
            assert srv._auto_discover_tools() is True
        assert called == [srv.mcp]

    def test_register_star_fallback(self):
        mod = ModuleType("y_tools")
        called = []
        mod.register_y_tools = lambda m: called.append(m)  # type: ignore[attr-defined]
        info = SimpleNamespace(name="y_tools")
        with patch("pkgutil.iter_modules", return_value=[info]), \
             patch("importlib.import_module", return_value=mod):
            assert srv._auto_discover_tools() is True
        assert called == [srv.mcp]

    def test_register_exception_skipped(self):
        mod = ModuleType("z_tools")

        def bad(m):
            raise RuntimeError("reg fail")

        mod.register = bad  # type: ignore[attr-defined]
        info = SimpleNamespace(name="z_tools")
        with patch("pkgutil.iter_modules", return_value=[info]), \
             patch("importlib.import_module", return_value=mod):
            assert srv._auto_discover_tools() is False

    def test_no_register_fn(self):
        mod = ModuleType("w_tools")
        info = SimpleNamespace(name="w_tools")
        with patch("pkgutil.iter_modules", return_value=[info]), \
             patch("importlib.import_module", return_value=mod):
            assert srv._auto_discover_tools() is False


class TestFallback:
    def test_fallback_registers(self):
        called = []
        fns = [lambda m: called.append("a"), lambda m: called.append("b")]
        with patch.object(srv, "register_memory_tools", fns[0]), \
             patch.object(srv, "register_workflow_tools", fns[1]), \
             patch.object(srv, "register_policy_tools", None), \
             patch.object(srv, "register_context_tools", fns[0]), \
             patch.object(srv, "register_seo_tools", fns[0]), \
             patch.object(srv, "register_ads_tools", fns[0]), \
             patch.object(srv, "register_analytics_tools", fns[0]), \
             patch.object(srv, "register_cro_tools", fns[0]), \
             patch.object(srv, "register_email_tools", fns[0]), \
             patch.object(srv, "register_freelance_tools", fns[0]), \
             patch.object(srv, "register_social_tools", fns[0]):
            srv._register_tools_fallback()
        assert "a" in called

    def test_fallback_exception_logged(self):
        def boom(m):
            raise RuntimeError("x")

        with patch.object(srv, "register_memory_tools", boom), \
             patch.object(srv, "register_workflow_tools", boom), \
             patch.object(srv, "register_policy_tools", boom), \
             patch.object(srv, "register_context_tools", boom), \
             patch.object(srv, "register_seo_tools", boom), \
             patch.object(srv, "register_ads_tools", boom), \
             patch.object(srv, "register_analytics_tools", boom), \
             patch.object(srv, "register_cro_tools", boom), \
             patch.object(srv, "register_email_tools", boom), \
             patch.object(srv, "register_freelance_tools", boom), \
             patch.object(srv, "register_social_tools", boom):
            srv._register_tools_fallback()  # no raise


class TestRbacWrap:
    def _fake_tool(self, name="t", is_async=False):
        tool = SimpleNamespace(name=name, is_async=is_async)
        tool.fn = lambda *a, **k: "ran"
        return tool

    def test_already_guarded_skipped(self):
        tool = self._fake_tool("dup")
        srv._GUARDED_TOOL_NAMES.add("dup")
        orig = tool.fn
        srv._wrap_tool_with_rbac(tool)
        assert tool.fn is orig
        srv._GUARDED_TOOL_NAMES.discard("dup")

    def test_denied_sync(self):
        tool = self._fake_tool("sync_tool")
        with patch.object(srv, "check_tool_permission", return_value=False):
            srv._wrap_tool_with_rbac(tool)
            out = json.loads(tool.fn())
        assert out == {"ok": False, "error": "permission denied"}
        srv._GUARDED_TOOL_NAMES.discard("sync_tool")

    def test_denied_on_exception(self):
        tool = self._fake_tool("exc_tool")
        with patch.object(srv, "check_tool_permission", side_effect=RuntimeError("x")):
            srv._wrap_tool_with_rbac(tool)
            out = json.loads(tool.fn())
        assert out["ok"] is False
        srv._GUARDED_TOOL_NAMES.discard("exc_tool")

    def test_allowed_sync(self):
        tool = self._fake_tool("ok_tool")
        with patch.object(srv, "check_tool_permission", return_value=True):
            srv._wrap_tool_with_rbac(tool)
            assert tool.fn() == "ran"
        srv._GUARDED_TOOL_NAMES.discard("ok_tool")

    def test_async_denied(self):
        import asyncio

        tool = self._fake_tool("async_tool", is_async=True)

        async def aorig(*a, **k):
            return "ran"

        tool.fn = aorig
        with patch.object(srv, "check_tool_permission", return_value=False):
            srv._wrap_tool_with_rbac(tool)
            out = json.loads(asyncio.run(tool.fn()))
        assert out["ok"] is False
        srv._GUARDED_TOOL_NAMES.discard("async_tool")

    def test_async_denied_on_exc(self):
        import asyncio

        tool = self._fake_tool("async_exc", is_async=True)

        async def aorig(*a, **k):
            return "ran"

        tool.fn = aorig
        with patch.object(srv, "check_tool_permission", side_effect=RuntimeError("x")):
            srv._wrap_tool_with_rbac(tool)
            out = json.loads(asyncio.run(tool.fn()))
        assert out["ok"] is False
        srv._GUARDED_TOOL_NAMES.discard("async_exc")

    def test_async_allowed(self):
        import asyncio

        tool = self._fake_tool("async_ok", is_async=True)

        async def aorig(*a, **k):
            return "ran"

        tool.fn = aorig
        with patch.object(srv, "check_tool_permission", return_value=True):
            srv._wrap_tool_with_rbac(tool)
            assert asyncio.run(tool.fn()) == "ran"
        srv._GUARDED_TOOL_NAMES.discard("async_ok")


class TestGuardedAddTool:
    def test_late_tool_guarded(self):
        new_tool = SimpleNamespace(name="late_tool", is_async=False)
        new_tool.fn = lambda: "x"
        with patch.object(srv, "_original_add_tool", return_value=None), \
             patch.object(srv._tool_manager, "get_tool", return_value=new_tool):
            srv._guarded_add_tool(SimpleNamespace(name="late_tool"))
        # The added tool's fn should now be RBAC-wrapped
        assert "late_tool" in srv._GUARDED_TOOL_NAMES
        srv._GUARDED_TOOL_NAMES.discard("late_tool")

    def test_add_tool_exception_swallowed(self):
        with patch.object(srv, "_original_add_tool", return_value=None), \
             patch.object(srv._tool_manager, "get_tool", side_effect=RuntimeError("x")):
            # Should not raise
            srv._guarded_add_tool(SimpleNamespace(name="whatever"))


class TestGracefulShutdown:
    def test_shutdown_raises_systemexit(self):
        with pytest.raises(SystemExit):
            srv._graceful_shutdown(15, None)

    def test_shutdown_storage_error(self):
        with patch("runtime.storage_backend.StorageFactory") as sf_mock:
            sf_mock.return_value.shutdown_all.side_effect = RuntimeError("x")
            with pytest.raises(SystemExit):
                srv._graceful_shutdown(15, None)


class TestResourceFallbacks:
    def test_rule_resource_unsafe(self):
        assert srv.get_rule_resource("../etc/passwd") == ""

    def test_workflow_resource_unsafe(self):
        assert srv.get_workflow_resource("../etc") == ""

    def test_workflow_missing(self):
        assert srv.get_workflow_resource("definitely-not-a-workflow-xyz") == ""
