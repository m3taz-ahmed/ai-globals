"""Tests for MCP client."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from runtime.mcp_client import McpClient, parse_mcp_command


def test_parse_mcp_command() -> None:
    assert parse_mcp_command("graphify.query({\"q\":\"test\"})") == ("graphify", "query", {"q": "test"})
    assert parse_mcp_command("context7.get-library-docs") == ("context7", "get-library-docs", {})
    assert parse_mcp_command("bad") is None


def test_parse_mcp_command_variants() -> None:
    assert parse_mcp_command("server.tool()") == ("server", "tool", {})
    assert parse_mcp_command(".tool") is None
    assert parse_mcp_command("server.") is None
    assert parse_mcp_command("server.tool(invalid json)") is None
    assert parse_mcp_command("  server.tool  ") == ("server", "tool", {})


def test_parse_mcp_command_non_dict_json() -> None:
    result = parse_mcp_command("server.tool([1, 2, 3])")
    assert result is not None
    _, _, args = result
    assert args == {}


def test_parse_mcp_command_nested_args() -> None:
    result = parse_mcp_command('freelancer.place_bid({"project_id": 123, "amount": 200.0})')
    assert result is not None
    _, _, args = result
    assert args["project_id"] == 123
    assert args["amount"] == 200.0


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


def test_mcp_client_loads_from_aios_config(tmp_path: Path) -> None:
    config_dir = tmp_path / "aios_mcp"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(
        json.dumps({"mcpServers": {"test-server": {"command": "echo", "args": ["hi"]}}}),
        encoding="utf-8",
    )
    client = McpClient("test-server", tmp_path)
    assert client.is_configured() is True
    assert client.config["command"] == "echo"


def test_mcp_client_call_tool_not_configured(tmp_path: Path) -> None:
    client = McpClient("unknown", tmp_path)
    result = client.call_tool("tool", {"arg": 1})
    assert result["ok"] is False
    assert "not configured" in result["error"]


def test_mcp_client_close_no_op(tmp_path: Path) -> None:
    client = McpClient("any", tmp_path)
    client.close()


def test_mcp_client_release_locked_no_process(tmp_path: Path) -> None:
    client = McpClient("any", tmp_path)
    client._release_locked()


def test_mcp_client_spawn_raises_when_not_configured(tmp_path: Path) -> None:
    client = McpClient("missing", tmp_path)
    with pytest.raises(RuntimeError, match="not configured"):
        client._spawn()


def test_mcp_client_key_is_tuple(tmp_path: Path) -> None:
    client = McpClient("server", tmp_path)
    assert client._key == ("server", tmp_path)
