"""Tests for plugins/linkedin/linkedin_plugin.py."""

from __future__ import annotations

import json
import warnings
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from plugins.linkedin.linkedin_plugin import LinkedInPlugin
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
def plugin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> LinkedInPlugin:
    _setup_root(tmp_path)
    monkeypatch.setenv("LINKEDIN_ACCESS_TOKEN", "test-token")
    kernel = Kernel(tmp_path)
    return LinkedInPlugin(kernel, None)


def test_on_load_with_env_token(plugin: LinkedInPlugin):
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        plugin.on_load()


def test_on_load_with_token_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _setup_root(tmp_path)
    monkeypatch.delenv("LINKEDIN_ACCESS_TOKEN", raising=False)
    monkeypatch.setenv("LINKEDIN_MCP_TOKEN_PATH", "/some/path/token.json")
    kernel = Kernel(tmp_path)
    p = LinkedInPlugin(kernel, None)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        p.on_load()


def test_on_load_warns_when_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _setup_root(tmp_path)
    monkeypatch.delenv("LINKEDIN_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("LINKEDIN_MCP_TOKEN_PATH", raising=False)
    kernel = Kernel(tmp_path)
    p = LinkedInPlugin(kernel, None)
    with pytest.warns(UserWarning, match="no access token found"):
        p.on_load()


def test_get_profile(plugin: LinkedInPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"name": "John Doe"}
        mock_factory.return_value = mock_client

        result = plugin.linkedin_get_profile()
        data = json.loads(result)
        assert data["name"] == "John Doe"
        mock_client.call_tool.assert_called_once_with("get_profile", {})


def test_create_post(plugin: LinkedInPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"ok": True}
        mock_factory.return_value = mock_client

        result = plugin.linkedin_create_post("Hello world", visibility="CONNECTIONS")
        data = json.loads(result)
        assert data["ok"] is True
        mock_client.call_tool.assert_called_once_with(
            "create_post", {"text": "Hello world", "visibility": "CONNECTIONS"}
        )


def test_create_post_default_visibility(plugin: LinkedInPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"ok": True}
        mock_factory.return_value = mock_client

        plugin.linkedin_create_post("Hello")
        mock_client.call_tool.assert_called_once_with(
            "create_post", {"text": "Hello", "visibility": "PUBLIC"}
        )


def test_share_link(plugin: LinkedInPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"ok": True}
        mock_factory.return_value = mock_client

        result = plugin.linkedin_share_link("Check this", "https://example.com")
        data = json.loads(result)
        assert data["ok"] is True
        mock_client.call_tool.assert_called_once_with(
            "share_link", {"text": "Check this", "url": "https://example.com"}
        )


def test_share_image(plugin: LinkedInPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"ok": True}
        mock_factory.return_value = mock_client

        result = plugin.linkedin_share_image("Photo", "/path/to/img.png")
        data = json.loads(result)
        assert data["ok"] is True
        mock_client.call_tool.assert_called_once_with(
            "share_image", {"text": "Photo", "image_path": "/path/to/img.png"}
        )


def test_delete_post(plugin: LinkedInPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"ok": True}
        mock_factory.return_value = mock_client

        result = plugin.linkedin_delete_post("urn:li:post:123")
        data = json.loads(result)
        assert data["ok"] is True
        mock_client.call_tool.assert_called_once_with(
            "delete_post", {"post_urn": "urn:li:post:123"}
        )


def test_create_draft(plugin: LinkedInPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"draft_id": "d1"}
        mock_factory.return_value = mock_client

        result = plugin.linkedin_create_draft("Draft text", kind="link")
        data = json.loads(result)
        assert data["draft_id"] == "d1"
        mock_client.call_tool.assert_called_once_with(
            "create_draft", {"text": "Draft text", "kind": "link"}
        )


def test_list_drafts_no_filter(plugin: LinkedInPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"drafts": []}
        mock_factory.return_value = mock_client

        result = plugin.linkedin_list_drafts()
        data = json.loads(result)
        assert "drafts" in data
        mock_client.call_tool.assert_called_once_with("list_drafts", {})


def test_list_drafts_with_status(plugin: LinkedInPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"drafts": []}
        mock_factory.return_value = mock_client

        plugin.linkedin_list_drafts(status="approved")
        mock_client.call_tool.assert_called_once_with("list_drafts", {"status": "approved"})


def test_get_draft(plugin: LinkedInPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"text": "draft"}
        mock_factory.return_value = mock_client

        result = plugin.linkedin_get_draft("d1")
        data = json.loads(result)
        assert data["text"] == "draft"
        mock_client.call_tool.assert_called_once_with("get_draft", {"draft_id": "d1"})


def test_update_draft(plugin: LinkedInPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"ok": True}
        mock_factory.return_value = mock_client

        result = plugin.linkedin_update_draft("d1", "new text")
        data = json.loads(result)
        assert data["ok"] is True
        mock_client.call_tool.assert_called_once_with(
            "update_draft", {"draft_id": "d1", "text": "new text"}
        )


def test_approve_draft_no_note(plugin: LinkedInPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"ok": True}
        mock_factory.return_value = mock_client

        result = plugin.linkedin_approve_draft("d1")
        data = json.loads(result)
        assert data["ok"] is True
        mock_client.call_tool.assert_called_once_with("approve_draft", {"draft_id": "d1"})


def test_approve_draft_with_note(plugin: LinkedInPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"ok": True}
        mock_factory.return_value = mock_client

        plugin.linkedin_approve_draft("d1", note="Looks good")
        mock_client.call_tool.assert_called_once_with(
            "approve_draft", {"draft_id": "d1", "note": "Looks good"}
        )


def test_delete_draft(plugin: LinkedInPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"ok": True}
        mock_factory.return_value = mock_client

        result = plugin.linkedin_delete_draft("d1")
        data = json.loads(result)
        assert data["ok"] is True
        mock_client.call_tool.assert_called_once_with("delete_draft", {"draft_id": "d1"})


def test_schedule_draft(plugin: LinkedInPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"ok": True}
        mock_factory.return_value = mock_client

        result = plugin.linkedin_schedule_draft("d1", "2026-07-02T09:00:00Z")
        data = json.loads(result)
        assert data["ok"] is True
        mock_client.call_tool.assert_called_once_with(
            "schedule_draft", {"draft_id": "d1", "publish_at": "2026-07-02T09:00:00Z"}
        )


def test_unschedule_draft(plugin: LinkedInPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"ok": True}
        mock_factory.return_value = mock_client

        result = plugin.linkedin_unschedule_draft("d1")
        data = json.loads(result)
        assert data["ok"] is True
        mock_client.call_tool.assert_called_once_with("unschedule_draft", {"draft_id": "d1"})


def test_publish_draft(plugin: LinkedInPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"ok": True}
        mock_factory.return_value = mock_client

        result = plugin.linkedin_publish_draft("d1")
        data = json.loads(result)
        assert data["ok"] is True
        mock_client.call_tool.assert_called_once_with("publish_draft", {"draft_id": "d1"})


def test_publish_due(plugin: LinkedInPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"published": 2}
        mock_factory.return_value = mock_client

        result = plugin.linkedin_publish_due()
        data = json.loads(result)
        assert data["published"] == 2
        mock_client.call_tool.assert_called_once_with("publish_due", {})


def test_list_comments(plugin: LinkedInPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"comments": []}
        mock_factory.return_value = mock_client

        result = plugin.linkedin_list_comments("urn:li:post:123")
        data = json.loads(result)
        assert "comments" in data
        mock_client.call_tool.assert_called_once_with(
            "list_comments", {"post_urn": "urn:li:post:123"}
        )


def test_reply_comment(plugin: LinkedInPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"ok": True}
        mock_factory.return_value = mock_client

        result = plugin.linkedin_reply_comment("urn:li:post:123", "Thanks!")
        data = json.loads(result)
        assert data["ok"] is True
        mock_client.call_tool.assert_called_once_with(
            "reply_comment", {"post_urn": "urn:li:post:123", "comment": "Thanks!"}
        )


def test_get_post_stats(plugin: LinkedInPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"likes": 10, "comments": 5}
        mock_factory.return_value = mock_client

        result = plugin.linkedin_get_post_stats("urn:li:post:123")
        data = json.loads(result)
        assert data["likes"] == 10
        mock_client.call_tool.assert_called_once_with(
            "get_post_stats", {"post_urn": "urn:li:post:123"}
        )


def test_proxy_handles_exception(plugin: LinkedInPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.side_effect = RuntimeError("auth failed")
        mock_factory.return_value = mock_client

        result = plugin.linkedin_get_profile()
        data = json.loads(result)
        assert data["ok"] is False
        assert "LinkedIn MCP call failed" in data["error"]
        assert "auth failed" in data["error"]


def test_proxy_returns_string_directly(plugin: LinkedInPlugin):
    with patch.object(plugin, "_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.call_tool.return_value = "raw string"
        mock_factory.return_value = mock_client

        result = plugin.linkedin_get_profile()
        assert result == "raw string"


def test_register_mcp_tools(plugin: LinkedInPlugin):
    tools = plugin.register_mcp_tools()
    assert len(tools) == 18


def test_client_creates_mcp_client(plugin: LinkedInPlugin):
    with patch("plugins.linkedin.linkedin_plugin.McpClient") as mock_cls:
        client = plugin._client()
        mock_cls.assert_called_once_with("linkedin", plugin.kernel.root)
        assert client is mock_cls.return_value
