"""Tests for plugins/fiverr/fiverr_plugin.py."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from plugins.fiverr.fiverr_plugin import FiverrPlugin
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
def plugin(tmp_path: Path) -> FiverrPlugin:
    _setup_root(tmp_path)
    kernel = Kernel(tmp_path)
    return FiverrPlugin(kernel, None)


def test_on_load_returns_none(plugin: FiverrPlugin):
    assert plugin.on_load() is None


def test_search_gigs_basic(plugin: FiverrPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"gigs": []}
        mock_factory.return_value = mock_client

        result = plugin.fiverr_search_gigs("logo design")
        data = json.loads(result)
        assert "gigs" in data
        mock_client.call_tool.assert_called_once_with(
            "search_gigs", {"query": "logo design", "sort_by": "relevance", "page": 1}
        )


def test_search_gigs_with_filters(plugin: FiverrPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"gigs": []}
        mock_factory.return_value = mock_client

        result = plugin.fiverr_search_gigs(
            "logo design", min_price=10.0, max_price=100.0, seller_level="top", sort_by="price", page=2
        )
        data = json.loads(result)
        assert "gigs" in data
        mock_client.call_tool.assert_called_once_with(
            "search_gigs",
            {
                "query": "logo design",
                "sort_by": "price",
                "page": 2,
                "min_price": 10.0,
                "max_price": 100.0,
                "seller_level": "top",
            },
        )


def test_get_gig_details(plugin: FiverrPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"title": "Gig Title"}
        mock_factory.return_value = mock_client

        result = plugin.fiverr_get_gig_details("gig123")
        data = json.loads(result)
        assert data["title"] == "Gig Title"
        mock_client.call_tool.assert_called_once_with("get_gig_details", {"gig_id": "gig123"})


def test_get_seller_profile(plugin: FiverrPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"name": "seller1"}
        mock_factory.return_value = mock_client

        result = plugin.fiverr_get_seller_profile("seller1")
        data = json.loads(result)
        assert data["name"] == "seller1"
        mock_client.call_tool.assert_called_once_with(
            "get_seller_profile", {"seller_username": "seller1"}
        )


def test_get_gig_reviews(plugin: FiverrPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"reviews": []}
        mock_factory.return_value = mock_client

        result = plugin.fiverr_get_gig_reviews("gig123")
        data = json.loads(result)
        assert "reviews" in data
        mock_client.call_tool.assert_called_once_with("get_gig_reviews", {"gig_id": "gig123"})


def test_list_categories(plugin: FiverrPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"categories": ["graphics", "writing"]}
        mock_factory.return_value = mock_client

        result = plugin.fiverr_list_categories()
        data = json.loads(result)
        assert "categories" in data
        mock_client.call_tool.assert_called_once_with("list_categories", {})


def test_proxy_handles_exception(plugin: FiverrPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.side_effect = ConnectionError("network down")
        mock_factory.return_value = mock_client

        result = plugin.fiverr_search_gigs("test")
        data = json.loads(result)
        assert data["ok"] is False
        assert "Fiverr MCP call failed" in data["error"]
        assert "network down" in data["error"]


def test_proxy_returns_string_directly(plugin: FiverrPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = "plain text result"
        mock_factory.return_value = mock_client

        result = plugin.fiverr_list_categories()
        assert result == "plain text result"


def test_register_mcp_tools(plugin: FiverrPlugin):
    tools = plugin.register_mcp_tools()
    assert len(tools) == 5
    assert plugin.fiverr_search_gigs in tools
    assert plugin.fiverr_get_gig_details in tools
    assert plugin.fiverr_get_seller_profile in tools
    assert plugin.fiverr_get_gig_reviews in tools
    assert plugin.fiverr_list_categories in tools


def test_client_creates_mcp_client(plugin: FiverrPlugin):
    with patch("plugins.fiverr.fiverr_plugin.McpClient") as mock_cls:
        client = plugin._client()
        mock_cls.assert_called_once_with("fiverr", plugin.kernel.root)
        assert client is mock_cls.return_value
