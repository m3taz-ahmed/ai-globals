"""Tests for plugins/freelancer/freelancer_plugin.py."""

from __future__ import annotations

import json
import warnings
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from plugins.freelancer.freelancer_plugin import FreelancerPlugin
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
def plugin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FreelancerPlugin:
    _setup_root(tmp_path)
    monkeypatch.setenv("FREELANCER_OAUTH_TOKEN", "test-token")
    kernel = Kernel(tmp_path)
    return FreelancerPlugin(kernel, None)


def test_on_load_with_token(plugin: FreelancerPlugin):
    # Should not warn when token is present
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        plugin.on_load()


def test_on_load_with_accounts_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _setup_root(tmp_path)
    monkeypatch.delenv("FREELANCER_OAUTH_TOKEN", raising=False)
    monkeypatch.setenv("FREELANCER_ACCOUNTS", '{"accounts": []}')
    kernel = Kernel(tmp_path)
    p = FreelancerPlugin(kernel, None)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        p.on_load()


def test_on_load_warns_when_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _setup_root(tmp_path)
    monkeypatch.delenv("FREELANCER_OAUTH_TOKEN", raising=False)
    monkeypatch.delenv("FREELANCER_ACCOUNTS", raising=False)
    kernel = Kernel(tmp_path)
    p = FreelancerPlugin(kernel, None)
    with pytest.warns(UserWarning, match="FREELANCER_OAUTH_TOKEN"):
        p.on_load()


def test_search_projects(plugin: FreelancerPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"projects": []}
        mock_factory.return_value = mock_client

        result = plugin.freelancer_search_projects("python", limit=5)
        data = json.loads(result)
        assert "projects" in data
        mock_client.call_tool.assert_called_once_with(
            "freelancer_search_projects", {"query": "python", "limit": 5}
        )


def test_get_project(plugin: FreelancerPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"title": "Project X"}
        mock_factory.return_value = mock_client

        result = plugin.freelancer_get_project(42)
        data = json.loads(result)
        assert data["title"] == "Project X"
        mock_client.call_tool.assert_called_once_with(
            "freelancer_get_project", {"project_id": 42}
        )


def test_my_projects(plugin: FreelancerPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"projects": []}
        mock_factory.return_value = mock_client

        result = plugin.freelancer_my_projects(status="completed")
        data = json.loads(result)
        assert "projects" in data
        mock_client.call_tool.assert_called_once_with(
            "freelancer_my_projects", {"status": "completed"}
        )


def test_my_bids(plugin: FreelancerPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"bids": []}
        mock_factory.return_value = mock_client

        result = plugin.freelancer_my_bids(status="lost")
        data = json.loads(result)
        assert "bids" in data
        mock_client.call_tool.assert_called_once_with(
            "freelancer_my_bids", {"status": "lost"}
        )


def test_place_bid(plugin: FreelancerPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"ok": True}
        mock_factory.return_value = mock_client

        result = plugin.freelancer_place_bid(42, 150.0, 7, "I can do it")
        data = json.loads(result)
        assert data["ok"] is True
        mock_client.call_tool.assert_called_once_with(
            "freelancer_place_bid",
            {"project_id": 42, "amount": 150.0, "days": 7, "description": "I can do it"},
        )


def test_get_milestones(plugin: FreelancerPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"milestones": []}
        mock_factory.return_value = mock_client

        result = plugin.freelancer_get_milestones(42)
        data = json.loads(result)
        assert "milestones" in data
        mock_client.call_tool.assert_called_once_with(
            "freelancer_get_milestones", {"project_id": 42}
        )


def test_list_threads(plugin: FreelancerPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"threads": []}
        mock_factory.return_value = mock_client

        result = plugin.freelancer_list_threads()
        data = json.loads(result)
        assert "threads" in data
        mock_client.call_tool.assert_called_once_with("freelancer_list_threads", {})


def test_get_messages(plugin: FreelancerPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"messages": []}
        mock_factory.return_value = mock_client

        result = plugin.freelancer_get_messages(99)
        data = json.loads(result)
        assert "messages" in data
        mock_client.call_tool.assert_called_once_with(
            "freelancer_get_messages", {"thread_id": 99}
        )


def test_send_message(plugin: FreelancerPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"ok": True}
        mock_factory.return_value = mock_client

        result = plugin.freelancer_send_message(99, "Hello there")
        data = json.loads(result)
        assert data["ok"] is True
        mock_client.call_tool.assert_called_once_with(
            "freelancer_send_message", {"thread_id": 99, "message": "Hello there"}
        )


def test_get_self(plugin: FreelancerPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"username": "me"}
        mock_factory.return_value = mock_client

        result = plugin.freelancer_get_self()
        data = json.loads(result)
        assert data["username"] == "me"
        mock_client.call_tool.assert_called_once_with("freelancer_get_self", {})


def test_list_accounts(plugin: FreelancerPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"accounts": []}
        mock_factory.return_value = mock_client

        result = plugin.freelancer_list_accounts()
        data = json.loads(result)
        assert "accounts" in data
        mock_client.call_tool.assert_called_once_with("freelancer_list_accounts", {})


def test_proxy_handles_exception(plugin: FreelancerPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.side_effect = RuntimeError("timeout")
        mock_factory.return_value = mock_client

        result = plugin.freelancer_get_self()
        data = json.loads(result)
        assert data["ok"] is False
        assert "Freelancer MCP call failed" in data["error"]
        assert "timeout" in data["error"]


def test_proxy_returns_string_directly(plugin: FreelancerPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = "raw text"
        mock_factory.return_value = mock_client

        result = plugin.freelancer_get_self()
        assert result == "raw text"


def test_register_mcp_tools(plugin: FreelancerPlugin):
    tools = plugin.register_mcp_tools()
    assert len(tools) == 11


def test_client_creates_mcp_client(plugin: FreelancerPlugin):
    with patch("plugins.freelancer.freelancer_plugin.McpClient") as mock_cls:
        client = plugin._client()
        mock_cls.assert_called_once_with("freelancer", plugin.kernel.root)
        assert client is mock_cls.return_value
