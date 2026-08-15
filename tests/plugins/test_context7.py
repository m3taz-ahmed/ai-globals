"""Tests for plugins/context7/context7_plugin.py."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from plugins.context7.context7_plugin import Context7Plugin
from runtime.kernel import Kernel


def _setup_root(tmp_path: Path) -> Path:
    for sub in ("runtime/policies", "workflows", "rules", "tech-stack", "state", "brain"):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    (tmp_path / "runtime/policies/default.yaml").write_text(
        "default_action: ask\nrules:\n"
        "  - name: allow-read\n    condition: \"type == 'Read'\"\n    action: allow\n"
    )
    return tmp_path


@pytest.fixture
def plugin(tmp_path: Path) -> Context7Plugin:
    _setup_root(tmp_path)
    kernel = Kernel(tmp_path)
    return Context7Plugin(kernel, None)


def test_on_load_returns_none(plugin: Context7Plugin):
    assert plugin.on_load() is None


def test_resolve_library_id_success(plugin: Context7Plugin):
    with patch.object(plugin, "_client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"id": "/upstash/context7", "name": "context7"}
        mock_client_factory.return_value = mock_client

        result = plugin.resolve_library_id("context7")
        data = json.loads(result)
        assert "id" in data
        mock_client.call_tool.assert_called_once_with(
            "resolve-library-id", {"libraryName": "context7"}
        )


def test_resolve_library_id_string_result(plugin: Context7Plugin):
    with patch.object(plugin, "_client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = "raw-string-result"
        mock_client_factory.return_value = mock_client

        result = plugin.resolve_library_id("react")
        assert result == "raw-string-result"


def test_get_library_docs_with_topic(plugin: Context7Plugin):
    with patch.object(plugin, "_client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"docs": "some docs"}
        mock_client_factory.return_value = mock_client

        result = plugin.get_library_docs("/upstash/context7", topic="authentication")
        data = json.loads(result)
        assert "docs" in data
        mock_client.call_tool.assert_called_once_with(
            "get-library-docs",
            {"context7LibraryId": "/upstash/context7", "topic": "authentication"},
        )


def test_get_library_docs_without_topic(plugin: Context7Plugin):
    with patch.object(plugin, "_client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"docs": "all docs"}
        mock_client_factory.return_value = mock_client

        result = plugin.get_library_docs("/upstash/context7")
        data = json.loads(result)
        assert "docs" in data
        mock_client.call_tool.assert_called_once_with(
            "get-library-docs", {"context7LibraryId": "/upstash/context7"}
        )


def test_proxy_handles_exception(plugin: Context7Plugin):
    with patch.object(plugin, "_client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client.call_tool.side_effect = RuntimeError("connection refused")
        mock_client_factory.return_value = mock_client

        result = plugin.resolve_library_id("react")
        data = json.loads(result)
        assert data["ok"] is False
        assert "Context7 MCP call failed" in data["error"]
        assert "connection refused" in data["error"]


def test_proxy_returns_dict_as_json(plugin: Context7Plugin):
    with patch.object(plugin, "_client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"key": "value", "nested": {"a": 1}}
        mock_client_factory.return_value = mock_client

        result = plugin.resolve_library_id("react")
        data = json.loads(result)
        assert data["key"] == "value"
        assert data["nested"]["a"] == 1


def test_register_mcp_tools(plugin: Context7Plugin):
    tools = plugin.register_mcp_tools()
    assert len(tools) == 2
    assert plugin.resolve_library_id in tools
    assert plugin.get_library_docs in tools


def test_client_creates_mcp_client(plugin: Context7Plugin):
    with patch("plugins.context7.context7_plugin.McpClient") as mock_cls:
        client = plugin._client()
        mock_cls.assert_called_once_with("context7", plugin.kernel.root)
        assert client is mock_cls.return_value
