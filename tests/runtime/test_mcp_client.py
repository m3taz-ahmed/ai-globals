"""Tests for MCP client."""

from __future__ import annotations

import json
from pathlib import Path

from runtime.mcp_client import McpClient, parse_mcp_command


def test_parse_mcp_command() -> None:
    assert parse_mcp_command("graphify.query({\"q\":\"test\"})") == ("graphify", "query", {"q": "test"})
    assert parse_mcp_command("context7.get-library-docs") == ("context7", "get-library-docs", {})
    assert parse_mcp_command("bad") is None


def test_mcp_client_loads_config(tmp_path: Path) -> None:
    settings = tmp_path / ".claude"
    settings.mkdir(parents=True, exist_ok=True)
    (settings / "settings.json").write_text(
        json.dumps({"mcpServers": {"graphify": {"command": "echo"}}}),
        encoding="utf-8",
    )
    client = McpClient("graphify", tmp_path)
    assert client.is_configured() is True
    client = McpClient("missing", tmp_path)
    assert client.is_configured() is False
