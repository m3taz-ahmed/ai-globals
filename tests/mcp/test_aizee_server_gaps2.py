"""Gap coverage for aizee_mcp/aizee_server.py — discovery + RBAC guard edges."""
from __future__ import annotations

import importlib
import types
from unittest.mock import MagicMock, patch

import pytest

import aizee_mcp.aizee_server as srv

pytestmark = pytest.mark.mcp


class TestDiscoveryEdges:
    def test_noncallable_register_candidate(self):
        """register_*_tools attr that isn't callable is skipped (80->77)."""
        fake_mod = types.SimpleNamespace()
        fake_mod.register_aaa_tools = "not callable"
        called = []

        def real_register(mcp):
            called.append(mcp)

        fake_mod.register_zzz_tools = real_register
        info = types.SimpleNamespace(name="fake_tools")
        with (
            patch("pkgutil.iter_modules", return_value=[info]),
            patch("importlib.import_module", return_value=fake_mod),
        ):
            assert srv._auto_discover_tools() is True
        assert called == [srv.mcp]

    def test_fallback_when_discovery_empty(self):
        """Module-level `if not _auto_discover_tools(): _register_tools_fallback()`."""
        with patch("pkgutil.iter_modules", return_value=[]):
            importlib.reload(srv)
        try:
            assert len(srv.mcp._tool_manager._tools) > 0
        finally:
            importlib.reload(srv)  # restore normal discovery state


class TestRbacGuardEdges:
    def test_apply_guard_tool_none(self):
        """Tool listed in _tools but get_tool returns None -> skipped."""
        fake_mgr = MagicMock()
        fake_mgr._tools = {"ghost": None}
        fake_mgr.get_tool.return_value = None
        with patch.object(srv, "_tool_manager", fake_mgr):
            srv._apply_rbac_guard()  # must not raise

    def test_guarded_add_tool_unknown(self):
        """Late-added tool not found in manager -> no wrap, no raise."""
        with (
            patch.object(srv, "_original_add_tool", return_value="ok") as orig,
            patch.object(srv._tool_manager, "get_tool", return_value=None),
        ):
            tool = MagicMock()
            tool.name = "phantom"
            assert srv._guarded_add_tool(tool) == "ok"
            orig.assert_called_once_with(tool)

    def test_guarded_add_tool_wrap_raises(self):
        """_wrap_tool_with_rbac raising is swallowed with a warning."""
        with (
            patch.object(srv, "_original_add_tool", return_value="ok"),
            patch.object(srv._tool_manager, "get_tool", return_value=MagicMock()),
            patch.object(srv, "_wrap_tool_with_rbac", side_effect=RuntimeError("x")),
        ):
            assert srv._guarded_add_tool(MagicMock(name="t")) == "ok"
