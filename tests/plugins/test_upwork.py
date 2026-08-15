"""Tests for plugins/upwork/upwork_plugin.py."""

from __future__ import annotations

import json
import warnings
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from plugins.upwork.upwork_plugin import UpworkPlugin
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
def plugin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> UpworkPlugin:
    _setup_root(tmp_path)
    monkeypatch.setenv("UPWORK_CLIENT_ID", "test-id")
    monkeypatch.setenv("UPWORK_CLIENT_SECRET", "test-secret")
    kernel = Kernel(tmp_path)
    return UpworkPlugin(kernel, None)


def test_on_load_with_credentials(plugin: UpworkPlugin):
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        plugin.on_load()


def test_on_load_warns_when_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _setup_root(tmp_path)
    monkeypatch.delenv("UPWORK_CLIENT_ID", raising=False)
    monkeypatch.delenv("UPWORK_CLIENT_SECRET", raising=False)
    kernel = Kernel(tmp_path)
    p = UpworkPlugin(kernel, None)
    with pytest.warns(UserWarning, match="UPWORK_CLIENT_ID"):
        p.on_load()


def test_on_load_warns_partial(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _setup_root(tmp_path)
    monkeypatch.setenv("UPWORK_CLIENT_ID", "test-id")
    monkeypatch.delenv("UPWORK_CLIENT_SECRET", raising=False)
    kernel = Kernel(tmp_path)
    p = UpworkPlugin(kernel, None)
    with pytest.warns(UserWarning, match="UPWORK_CLIENT_SECRET"):
        p.on_load()


def test_search_jobs(plugin: UpworkPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"jobs": []}
        mock_factory.return_value = mock_client

        result = plugin.upwork_search_jobs("python developer", limit=5)
        data = json.loads(result)
        assert "jobs" in data
        mock_client.call_tool.assert_called_once_with(
            "search_jobs", {"query": "python developer", "limit": 5}
        )


def test_search_jobs_default_limit(plugin: UpworkPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"jobs": []}
        mock_factory.return_value = mock_client

        plugin.upwork_search_jobs("react")
        mock_client.call_tool.assert_called_once_with(
            "search_jobs", {"query": "react", "limit": 10}
        )


def test_get_job_details(plugin: UpworkPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"title": "Job X"}
        mock_factory.return_value = mock_client

        result = plugin.upwork_get_job_details("job123")
        data = json.loads(result)
        assert data["title"] == "Job X"
        mock_client.call_tool.assert_called_once_with(
            "get_job_details", {"job_id": "job123"}
        )


def test_get_profile(plugin: UpworkPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"name": "Freelancer"}
        mock_factory.return_value = mock_client

        result = plugin.upwork_get_profile()
        data = json.loads(result)
        assert data["name"] == "Freelancer"
        mock_client.call_tool.assert_called_once_with("get_profile", {})


def test_list_contracts(plugin: UpworkPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"contracts": []}
        mock_factory.return_value = mock_client

        result = plugin.upwork_list_contracts(status="completed")
        data = json.loads(result)
        assert "contracts" in data
        mock_client.call_tool.assert_called_once_with(
            "list_contracts", {"status": "completed"}
        )


def test_get_balance(plugin: UpworkPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"balance": 500.0}
        mock_factory.return_value = mock_client

        result = plugin.upwork_get_balance()
        data = json.loads(result)
        assert data["balance"] == 500.0
        mock_client.call_tool.assert_called_once_with("get_balance", {})


def test_list_saved_jobs(plugin: UpworkPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"saved": []}
        mock_factory.return_value = mock_client

        result = plugin.upwork_list_saved_jobs()
        data = json.loads(result)
        assert "saved" in data
        mock_client.call_tool.assert_called_once_with("list_saved_jobs", {})


def test_save_job(plugin: UpworkPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"ok": True}
        mock_factory.return_value = mock_client

        result = plugin.upwork_save_job("job123")
        data = json.loads(result)
        assert data["ok"] is True
        mock_client.call_tool.assert_called_once_with("save_job", {"job_id": "job123"})


def test_get_proposal_stats(plugin: UpworkPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"submitted": 10}
        mock_factory.return_value = mock_client

        result = plugin.upwork_get_proposal_stats()
        data = json.loads(result)
        assert data["submitted"] == 10
        mock_client.call_tool.assert_called_once_with("get_proposal_stats", {})


def test_proxy_handles_exception(plugin: UpworkPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.side_effect = RuntimeError("auth error")
        mock_factory.return_value = mock_client

        result = plugin.upwork_get_profile()
        data = json.loads(result)
        assert data["ok"] is False
        assert "Upwork MCP call failed" in data["error"]
        assert "auth error" in data["error"]


def test_proxy_returns_string_directly(plugin: UpworkPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = "raw text"
        mock_factory.return_value = mock_client

        result = plugin.upwork_get_profile()
        assert result == "raw text"


def test_register_mcp_tools(plugin: UpworkPlugin):
    tools = plugin.register_mcp_tools()
    assert len(tools) == 8


def test_client_creates_mcp_client(plugin: UpworkPlugin):
    with patch("plugins.upwork.upwork_plugin.McpClient") as mock_cls:
        client = plugin._client()
        mock_cls.assert_called_once_with("upwork", plugin.kernel.root)
        assert client is mock_cls.return_value
