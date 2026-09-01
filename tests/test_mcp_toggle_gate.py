"""Tests for the dashboard MCP-toggle enable-gate.

Verifies that toggling an MCP server OFF in dashboard settings:
- blocks tool calls (no process spawn) and returns a disabled error, and
- hides the server's tools from PluginManager.get_tools().

FAST tier — no real subprocess, no model loading.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest

from runtime import mcp_client
from runtime.mcp_client import McpClient
from runtime.settings import (
    SettingsManager,
    clear_settings_cache,
    get_settings_manager,
    reload_settings_manager,
)

# -- Fixtures -----------------------------------------------------------------


@pytest.fixture
def tmp_root(tmp_path: Path) -> Path:
    """Temp OS root with state/ + a 3-server MCP config.json."""
    (tmp_path / "state").mkdir()
    mcp_config = tmp_path / "aizee_mcp" / "config.json"
    mcp_config.parent.mkdir()
    mcp_config.write_text(
        json.dumps({"mcpServers": {"aizee": {}, "youtube": {"command": "node"}, "upwork": {}}}),
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture(autouse=True)
def _reset_caches():
    """Isolate tests from the process-wide settings cache."""
    clear_settings_cache()
    mcp_client._PROC_POOL.clear()
    mcp_client._PROC_INIT.clear()
    mcp_client._SEND_LOCKS.clear()
    yield
    clear_settings_cache()
    mcp_client._PROC_POOL.clear()
    mcp_client._PROC_INIT.clear()
    mcp_client._SEND_LOCKS.clear()


def _sm(tmp_root: Path) -> SettingsManager:
    return SettingsManager(tmp_root, tmp_root / "aizee_mcp" / "config.json")


def _disable(sm: SettingsManager, name: str) -> None:
    sm.update_section("mcp_servers", {name: {"enabled": False}})


# -- McpClient enable-gate (block) -------------------------------------------


class TestMcpClientGate:
    def test_call_tool_blocked_when_disabled(self, tmp_root: Path) -> None:
        sm = _sm(tmp_root)
        _disable(sm, "youtube")
        client = McpClient("youtube", tmp_root, settings_manager=sm)
        # Config exists (command=node) so is_configured() is True, but the
        # gate must still block the call without spawning anything.
        assert client.is_configured() is True
        result = client.call_tool("list_videos", {"channel_id": "x"})
        assert result["ok"] is False
        assert result.get("disabled") is True
        assert "disabled" in result["error"]
        # No process was spawned.
        assert mcp_client._PROC_POOL == {}

    def test_async_call_tool_blocked_when_disabled(self, tmp_root: Path) -> None:
        import asyncio

        sm = _sm(tmp_root)
        _disable(sm, "youtube")
        client = McpClient("youtube", tmp_root, settings_manager=sm)
        result = asyncio.run(client.async_call_tool("list_videos", {"channel_id": "x"}))
        assert result["ok"] is False
        assert result.get("disabled") is True
        assert mcp_client._PROC_POOL == {}

    def test_is_enabled_reflects_toggle(self, tmp_root: Path) -> None:
        sm = _sm(tmp_root)
        client = McpClient("youtube", tmp_root, settings_manager=sm)
        assert client.is_enabled() is True
        _disable(sm, "youtube")
        assert client.is_enabled() is False

    def test_unknown_server_defaults_enabled(self, tmp_root: Path) -> None:
        sm = _sm(tmp_root)
        client = McpClient("does-not-exist", tmp_root, settings_manager=sm)
        assert client.is_enabled() is True

    def test_call_tool_proceeds_when_enabled(self, tmp_root: Path) -> None:
        """When enabled, call_tool must NOT short-circuit on the disabled gate."""
        sm = _sm(tmp_root)
        client = McpClient("youtube", tmp_root, settings_manager=sm)
        assert client.is_enabled() is True
        # Stub the async path so no real subprocess is spawned. If the gate
        # fired, async_call_tool would never be called and result would be
        # the disabled payload.
        client.async_call_tool = AsyncMock(return_value={"ok": True, "result": {}})  # type: ignore[assignment]
        result = client.call_tool("list_videos", {"channel_id": "x"})
        assert result["ok"] is True
        assert client.async_call_tool.called

    def test_re_enable_after_toggle_restores_calls(self, tmp_root: Path) -> None:
        sm = _sm(tmp_root)
        _disable(sm, "youtube")
        client = McpClient("youtube", tmp_root, settings_manager=sm)
        assert client.call_tool("list_videos", {})["ok"] is False
        # Re-enable
        sm.update_section("mcp_servers", {"youtube": {"enabled": True}})
        client.async_call_tool = AsyncMock(return_value={"ok": True, "result": {}})  # type: ignore[assignment]
        assert client.call_tool("list_videos", {})["ok"] is True


# -- Shared settings manager cache -------------------------------------------


class TestSettingsCache:
    def test_get_settings_manager_returns_shared_instance(self, tmp_root: Path) -> None:
        a = get_settings_manager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        b = get_settings_manager(tmp_root)
        assert a is b

    def test_reload_settings_manager_picks_up_disk_change(self, tmp_root: Path) -> None:
        sm = get_settings_manager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        assert sm.is_mcp_enabled("youtube") is True
        # Write a settings file directly with youtube disabled.
        (tmp_root / "state" / "settings.json").write_text(
            json.dumps({"version": 2, "mcp_servers": {"youtube": {"enabled": False}}}),
            encoding="utf-8",
        )
        reload_settings_manager(tmp_root)
        assert sm.is_mcp_enabled("youtube") is False

    def test_mcpclient_uses_shared_manager(self, tmp_root: Path) -> None:
        """McpClient without an injected manager resolves the shared one."""
        shared = get_settings_manager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        _disable(shared, "youtube")
        # No settings_manager passed — must still pick up the disabled state.
        client = McpClient("youtube", tmp_root)
        assert client.is_enabled() is False
        assert client.call_tool("list_videos", {})["ok"] is False


# -- PluginManager.get_tools() hide ------------------------------------------


class TestPluginHide:
    def test_disabled_plugin_tools_hidden(self, tmp_root: Path) -> None:
        from runtime.plugin import PluginManager

        sm = _sm(tmp_root)
        _disable(sm, "youtube")

        # Minimal fake kernel exposing settings_manager + a plugins dict.
        class _FakeKernel:
            settings_manager = sm

        class _YoutubePlugin:
            name = "youtube"

            def register_mcp_tools(self) -> list[Any]:
                return [lambda: "yt-tool"]

        class _TwitterPlugin:
            name = "twitter"

            def register_mcp_tools(self) -> list[Any]:
                return [lambda: "tw-tool"]

        mgr = PluginManager.__new__(PluginManager)
        mgr.kernel = _FakeKernel()  # type: ignore[assignment]
        mgr._plugins = {"youtube": _YoutubePlugin(), "twitter": _TwitterPlugin()}  # type: ignore[assignment,dict-item]
        mgr._guards = {}

        tools = mgr.get_tools()
        # youtube disabled → its tool hidden; twitter still present.
        assert len(tools) == 1

    def test_enabled_plugin_tools_visible(self, tmp_root: Path) -> None:
        from runtime.plugin import PluginManager

        sm = _sm(tmp_root)  # all enabled by default

        class _FakeKernel:
            settings_manager = sm

        class _YoutubePlugin:
            name = "youtube"

            def register_mcp_tools(self) -> list[Any]:
                return [lambda: "yt-tool"]

        mgr = PluginManager.__new__(PluginManager)
        mgr.kernel = _FakeKernel()  # type: ignore[assignment]
        mgr._plugins = {"youtube": _YoutubePlugin()}  # type: ignore[assignment,dict-item]
        mgr._guards = {}

        assert len(mgr.get_tools()) == 1

    def test_no_settings_manager_falls_back_to_all_tools(self, tmp_root: Path) -> None:
        """If the kernel lacks settings_manager, no plugin is hidden (fail-open)."""
        from runtime.plugin import PluginManager

        class _FakeKernel:
            pass  # no settings_manager attribute

        class _YoutubePlugin:
            name = "youtube"

            def register_mcp_tools(self) -> list[Any]:
                return [lambda: "yt-tool"]

        mgr = PluginManager.__new__(PluginManager)
        mgr.kernel = _FakeKernel()  # type: ignore[assignment]
        mgr._plugins = {"youtube": _YoutubePlugin()}  # type: ignore[assignment,dict-item]
        mgr._guards = {}

        assert len(mgr.get_tools()) == 1
