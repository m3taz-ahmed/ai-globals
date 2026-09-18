"""Gap tests for runtime/mcp_client.py."""
from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest

from runtime.mcp_client import McpClient


def _client(tmp_path, name: str = "srv") -> McpClient:
    settings = MagicMock()
    settings.is_mcp_enabled.return_value = True
    return McpClient(name, tmp_path, settings_manager=settings)


class TestEnabledGate:
    def test_settings_error_fails_closed(self, tmp_path):
        settings = MagicMock()
        settings.is_mcp_enabled.side_effect = RuntimeError("boom")
        c = McpClient("srv", tmp_path, settings_manager=settings)
        assert c.is_enabled() is False

    def test_disabled_sync_call(self, tmp_path):
        settings = MagicMock()
        settings.is_mcp_enabled.return_value = False
        c = McpClient("srv", tmp_path, settings_manager=settings)
        out = c._call_tool_sync("t", {})
        assert out["ok"] is False

    def test_unconfigured_sync_call(self, tmp_path):
        c = _client(tmp_path)
        out = c._call_tool_sync("t", {})
        assert out["ok"] is False
        assert "not configured" in out["error"]


class TestLoadConfig:
    def test_bad_json_skipped(self, tmp_path):
        (tmp_path / "aizee_mcp").mkdir()
        (tmp_path / "aizee_mcp" / "config.json").write_text("{bad", encoding="utf-8")
        c = _client(tmp_path)
        assert c.config == {}

    def test_non_dict_skipped(self, tmp_path):
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".claude" / "settings.json").write_text("[1,2]", encoding="utf-8")
        c = _client(tmp_path)
        assert c.config == {}

    def test_servers_not_dict(self, tmp_path):
        (tmp_path / "aizee_mcp").mkdir()
        (tmp_path / "aizee_mcp" / "config.json").write_text(
            json.dumps({"mcpServers": "notadict"}), encoding="utf-8")
        c = _client(tmp_path)
        assert c.config == {}

    def test_server_entry_not_dict(self, tmp_path):
        (tmp_path / "aizee_mcp").mkdir()
        (tmp_path / "aizee_mcp" / "config.json").write_text(
            json.dumps({"mcpServers": {"srv": "scalar"}}), encoding="utf-8")
        c = _client(tmp_path, "srv")
        assert c.config == {}

    def test_found_config(self, tmp_path):
        (tmp_path / "aizee_mcp").mkdir()
        (tmp_path / "aizee_mcp" / "config.json").write_text(
            json.dumps({"mcpServers": {"srv": {"command": "python", "args": ["-m", "x"]}}}),
            encoding="utf-8")
        c = _client(tmp_path, "srv")
        assert c.config["command"] == "python"


class TestSpawnEnv:
    def test_passthrough(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AIZEE_MCP_ENV_PASSTHROUGH", "1")
        monkeypatch.setenv("MY_SECRET_MARKER", "yes")
        c = _client(tmp_path)
        env = c._build_spawn_env()
        assert env["MY_SECRET_MARKER"] == "yes"

    def test_allowlist(self, tmp_path, monkeypatch):
        monkeypatch.delenv("AIZEE_MCP_ENV_PASSTHROUGH", raising=False)
        monkeypatch.setenv("AIZEE_MCP_ENV_ALLOWLIST", "EXTRA_VAR")
        monkeypatch.setenv("EXTRA_VAR", "v1")
        monkeypatch.setenv("NOT_ALLOWED_XYZ", "no")
        c = _client(tmp_path)
        env = c._build_spawn_env()
        assert env.get("EXTRA_VAR") == "v1"
        assert "NOT_ALLOWED_XYZ" not in env
        assert env["AIZEE_ROOT"] == str(tmp_path)


class TestSend:
    def test_no_pipes(self, tmp_path):
        c = _client(tmp_path)
        proc = MagicMock()
        proc.stdin = None
        proc.stdout = None
        with pytest.raises(RuntimeError, match="pipes"):
            c._send(proc, {})

    def test_non_json_lines_then_json(self, tmp_path):
        c = _client(tmp_path)
        proc = MagicMock()
        proc.stdout = MagicMock()
        lines = iter(["not json", "{bad", json.dumps({"r": 1})])
        with patch.object(McpClient, "_read_stdout", side_effect=lambda *a, **k: next(lines)):
            out = c._send(proc, {"m": 1})
        assert out == {"r": 1}

    def test_all_non_json_raises(self, tmp_path):
        c = _client(tmp_path)
        proc = MagicMock()
        with patch.object(McpClient, "_read_stdout", return_value="junk"):
            with pytest.raises(RuntimeError):
                c._send(proc, {})

    def test_exception_result_raises(self, tmp_path):
        c = _client(tmp_path)
        proc = MagicMock()
        with patch.object(McpClient, "_read_stdout", return_value=ValueError("io")):
            with pytest.raises(ValueError):
                c._send(proc, {})

    def test_empty_line_then_json(self, tmp_path):
        c = _client(tmp_path)
        proc = MagicMock()
        lines = iter(["   ", json.dumps({"ok": 1})])
        with patch.object(McpClient, "_read_stdout", side_effect=lambda *a, **k: next(lines)):
            with pytest.raises(RuntimeError, match="closed stdout"):
                c._send(proc, {})


class TestAsyncSpawn:
    def test_args_not_list(self, tmp_path):
        c = _client(tmp_path)
        c.config = {"command": "python", "args": "notalist"}
        out = asyncio.run(c._async_spawn())
        assert out["ok"] is False
        assert "list" in out["error"]

    def test_rejected_command(self, tmp_path):
        c = _client(tmp_path)
        c.config = {"command": "rm -rf /", "args": []}
        out = asyncio.run(c._async_spawn())
        assert out["ok"] is False

    def test_which_resolution(self, tmp_path, monkeypatch):
        c = _client(tmp_path)
        c.config = {"command": "python", "args": []}
        monkeypatch.setenv("AIZEE_MCP_ENV_PASSTHROUGH", "1")
        with patch("runtime.mcp_client.asyncio.create_subprocess_exec") as spawn:
            spawn.side_effect = OSError("cannot spawn")
            out = asyncio.run(c._async_spawn())
        assert out["ok"] is False

    def test_call_tool_in_running_loop(self, tmp_path):
        c = _client(tmp_path)
        async def go():
            with patch.object(McpClient, "_call_tool_sync", return_value={"ok": True, "sync": 1}) as m:
                out = c.call_tool("t", {})
                assert out["sync"] == 1
                m.assert_called_once()
        asyncio.run(go())
