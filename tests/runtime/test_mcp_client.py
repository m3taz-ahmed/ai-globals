"""Tests for MCP client."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from runtime import mcp_client
from runtime.mcp_client import McpClient, parse_mcp_command


@pytest.fixture(autouse=True)
def _reset_mcp_state():
    """Reset module-level pools/flags between tests."""
    mcp_client._PROC_POOL.clear()
    mcp_client._PROC_INIT.clear()
    mcp_client._SEND_LOCKS.clear()
    mcp_client._SECRETS_LOADED = False
    yield
    mcp_client._PROC_POOL.clear()
    mcp_client._PROC_INIT.clear()
    mcp_client._SEND_LOCKS.clear()


def _make_config_dir(tmp_path: Path, server: str = "test", command: str = "echo") -> Path:
    settings = tmp_path / ".claude"
    settings.mkdir(parents=True, exist_ok=True)
    (settings / "settings.json").write_text(
        json.dumps({"mcpServers": {server: {"command": command, "args": ["--flag"]}}}),
        encoding="utf-8",
    )
    return tmp_path


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


def test_parse_mcp_command_empty_server_with_parens() -> None:
    # head=".tool", partition "." -> server="" -> line 375 return None
    assert parse_mcp_command(".tool(") is None
    assert parse_mcp_command("server.(") is None


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


# ---------------------------------------------------------------------------
# _load_secrets_once
# ---------------------------------------------------------------------------


def test_load_secrets_once_no_env_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AGENT_OS_ROOT", str(tmp_path))
    mcp_client._SECRETS_LOADED = False
    mcp_client._load_secrets_once()
    assert mcp_client._SECRETS_LOADED is True


def test_load_secrets_once_loads_env(tmp_path: Path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# comment\n"
        "\n"
        "export API_KEY=secret123\n"
        'QUOTED="double_quoted"\n'
        "SINGLE='single_quoted'\n"
        "SKIP_ME=your_api_key\n"
        "NOEQUALS\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("AGENT_OS_ROOT", str(tmp_path))
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("QUOTED", raising=False)
    monkeypatch.delenv("SINGLE", raising=False)
    monkeypatch.delenv("SKIP_ME", raising=False)
    mcp_client._SECRETS_LOADED = False
    mcp_client._load_secrets_once()
    assert os.environ.get("API_KEY") == "secret123"
    assert os.environ.get("QUOTED") == "double_quoted"
    assert os.environ.get("SINGLE") == "single_quoted"
    assert "SKIP_ME" not in os.environ or os.environ.get("SKIP_ME") != "your_api_key"


def test_load_secrets_once_skipped_if_already_loaded(tmp_path: Path, monkeypatch) -> None:
    mcp_client._SECRETS_LOADED = True
    monkeypatch.setenv("AGENT_OS_ROOT", str(tmp_path / "nonexistent"))
    mcp_client._load_secrets_once()  # should be no-op
    assert mcp_client._SECRETS_LOADED is True


def test_load_secrets_once_fallback_to_parent_dir(tmp_path: Path, monkeypatch) -> None:
    # AGENT_OS_ROOT points to nonexistent; fallback uses __file__.parent.parent
    monkeypatch.setenv("AGENT_OS_ROOT", str(tmp_path / "nope"))
    mcp_client._SECRETS_LOADED = False
    # Should not raise even if fallback .env doesn't exist
    mcp_client._load_secrets_once()
    assert mcp_client._SECRETS_LOADED is True


# ---------------------------------------------------------------------------
# _user_script_dirs / _user_site_dirs
# ---------------------------------------------------------------------------


def test_user_script_dirs_returns_list(monkeypatch) -> None:
    with patch("sysconfig.get_path", return_value="/fake/scripts"):
        with patch("sysconfig.get_config_var", return_value="/fake/userbase"):
            result = mcp_client._user_script_dirs()
    assert isinstance(result, list)


def test_user_script_dirs_empty_scripts(monkeypatch) -> None:
    with patch("sysconfig.get_path", return_value=""):
        with patch("sysconfig.get_config_var", return_value=None):
            result = mcp_client._user_script_dirs()
    assert result == []


def test_user_site_dirs(monkeypatch) -> None:
    with patch("sysconfig.get_path", return_value="/fake/purelib"):
        result = mcp_client._user_site_dirs()
    assert result == ["/fake/purelib"]


def test_user_site_dirs_empty(monkeypatch) -> None:
    with patch("sysconfig.get_path", return_value=""):
        result = mcp_client._user_site_dirs()
    assert result == []


# ---------------------------------------------------------------------------
# _terminate_pool
# ---------------------------------------------------------------------------


def test_terminate_pool_terminates_and_kills() -> None:
    proc_alive = MagicMock(spec=subprocess.Popen)
    proc_alive.poll.return_value = None
    proc_alive.wait.side_effect = subprocess.TimeoutExpired("cmd", 2)
    proc_dead = MagicMock(spec=subprocess.Popen)
    proc_dead.poll.return_value = 0
    mcp_client._PROC_POOL[("s", Path("/x"))] = proc_alive
    mcp_client._PROC_POOL[("d", Path("/x"))] = proc_dead
    mcp_client._PROC_INIT[("s", Path("/x"))] = True
    mcp_client._terminate_pool()
    proc_alive.kill.assert_called_once()
    assert mcp_client._PROC_POOL == {}
    assert mcp_client._PROC_INIT == {}


# ---------------------------------------------------------------------------
# _spawn
# ---------------------------------------------------------------------------


def test_spawn_calls_popen(tmp_path: Path) -> None:
    _make_config_dir(tmp_path)
    client = McpClient("test", tmp_path)
    mock_proc = MagicMock(spec=subprocess.Popen)
    with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
        with patch("shutil.which", return_value="/resolved/echo"):
            with patch("runtime.mcp_client._user_script_dirs", return_value=["/extra"]):
                with patch("runtime.mcp_client._user_site_dirs", return_value=["/site"]):
                    proc = client._spawn()
    assert proc is mock_proc
    mock_popen.assert_called_once()
    args, kwargs = mock_popen.call_args
    # command resolved via shutil.which
    assert args[0][0] == "/resolved/echo"
    assert "--flag" in args[0]
    assert kwargs["cwd"] == str(tmp_path)


def test_spawn_no_resolution_when_which_returns_none(tmp_path: Path) -> None:
    _make_config_dir(tmp_path, command="custom-cmd")
    client = McpClient("test", tmp_path)
    mock_proc = MagicMock(spec=subprocess.Popen)
    with patch("subprocess.Popen", return_value=mock_proc):
        with patch("shutil.which", return_value=None):
            with patch("runtime.mcp_client._user_script_dirs", return_value=[]):
                with patch("runtime.mcp_client._user_site_dirs", return_value=[]):
                    proc = client._spawn()
    assert proc is mock_proc


# ---------------------------------------------------------------------------
# _send
# ---------------------------------------------------------------------------


def _mock_proc_with_io(response: str) -> MagicMock:
    proc = MagicMock(spec=subprocess.Popen)
    proc.stdin = MagicMock()
    proc.stdout = MagicMock()
    proc.stdout.readline.return_value = response
    proc.poll.return_value = None
    return proc


def test_send_success(tmp_path: Path) -> None:
    _make_config_dir(tmp_path)
    client = McpClient("test", tmp_path)
    proc = _mock_proc_with_io('{"jsonrpc":"2.0","result":{}}\n')
    result = client._send(proc, {"method": "test"})
    assert result["result"] == {}


def test_send_no_pipes_raises(tmp_path: Path) -> None:
    _make_config_dir(tmp_path)
    client = McpClient("test", tmp_path)
    proc = MagicMock(spec=subprocess.Popen)
    proc.stdin = None
    proc.stdout = None
    with pytest.raises(RuntimeError, match="pipes not available"):
        client._send(proc, {"method": "test"})


def test_send_timeout(tmp_path: Path) -> None:
    _make_config_dir(tmp_path)
    client = McpClient("test", tmp_path)
    proc = MagicMock(spec=subprocess.Popen)
    proc.stdin = MagicMock()
    proc.stdout = MagicMock()
    proc.stdout.readline.side_effect = lambda: (_ for _ in ()).throw(StopIteration())
    # Simulate blocking readline by making the queue empty
    import queue as q_module

    with patch("queue.Queue.get", side_effect=q_module.Empty):
        with pytest.raises(TimeoutError, match="timed out"):
            client._send(proc, {"method": "test"}, timeout=0.1)


def test_send_reader_exception(tmp_path: Path) -> None:
    _make_config_dir(tmp_path)
    client = McpClient("test", tmp_path)
    proc = MagicMock(spec=subprocess.Popen)
    proc.stdin = MagicMock()
    proc.stdout = MagicMock()
    proc.stdout.readline.side_effect = OSError("read failed")
    with pytest.raises(OSError, match="read failed"):
        client._send(proc, {"method": "test"}, timeout=2)


def test_send_empty_result_raises(tmp_path: Path) -> None:
    _make_config_dir(tmp_path)
    client = McpClient("test", tmp_path)
    proc = _mock_proc_with_io("")
    with pytest.raises(RuntimeError, match="closed stdout"):
        client._send(proc, {"method": "test"})


# ---------------------------------------------------------------------------
# _ensure_process / _release_locked
# ---------------------------------------------------------------------------


def test_ensure_process_spawns_and_initializes(tmp_path: Path) -> None:
    _make_config_dir(tmp_path)
    client = McpClient("test", tmp_path)
    mock_proc = _mock_proc_with_io('{"jsonrpc":"2.0","result":{}}\n')
    with patch("subprocess.Popen", return_value=mock_proc):
        with patch("shutil.which", return_value=None):
            with patch("runtime.mcp_client._user_script_dirs", return_value=[]):
                with patch("runtime.mcp_client._user_site_dirs", return_value=[]):
                    proc = client._ensure_process()
    assert proc is mock_proc
    assert mcp_client._PROC_INIT[client._key] is True
    # Second call reuses
    proc2 = client._ensure_process()
    assert proc2 is mock_proc


def test_ensure_process_reap_dead_process(tmp_path: Path) -> None:
    _make_config_dir(tmp_path)
    client = McpClient("test", tmp_path)
    dead_proc = MagicMock(spec=subprocess.Popen)
    dead_proc.poll.return_value = 1  # dead
    dead_proc.wait.return_value = 0
    mcp_client._PROC_POOL[client._key] = dead_proc
    mcp_client._PROC_INIT[client._key] = True
    new_proc = _mock_proc_with_io('{"jsonrpc":"2.0","result":{}}\n')
    with patch("subprocess.Popen", return_value=new_proc):
        with patch("shutil.which", return_value=None):
            with patch("runtime.mcp_client._user_script_dirs", return_value=[]):
                with patch("runtime.mcp_client._user_site_dirs", return_value=[]):
                    proc = client._ensure_process()
    assert proc is new_proc


def test_ensure_process_dead_proc_wait_timeout(tmp_path: Path) -> None:
    _make_config_dir(tmp_path)
    client = McpClient("test", tmp_path)
    dead_proc = MagicMock(spec=subprocess.Popen)
    dead_proc.poll.return_value = 1
    dead_proc.wait.side_effect = subprocess.TimeoutExpired("cmd", 1)
    mcp_client._PROC_POOL[client._key] = dead_proc
    mcp_client._PROC_INIT[client._key] = True
    new_proc = _mock_proc_with_io('{"jsonrpc":"2.0","result":{}}\n')
    with patch("subprocess.Popen", return_value=new_proc):
        with patch("shutil.which", return_value=None):
            with patch("runtime.mcp_client._user_script_dirs", return_value=[]):
                with patch("runtime.mcp_client._user_site_dirs", return_value=[]):
                    proc = client._ensure_process()
    dead_proc.kill.assert_called_once()
    assert proc is new_proc


def test_ensure_process_init_error_releases(tmp_path: Path) -> None:
    _make_config_dir(tmp_path)
    client = McpClient("test", tmp_path)
    mock_proc = _mock_proc_with_io('{"jsonrpc":"2.0","error":"init failed"}\n')
    with patch("subprocess.Popen", return_value=mock_proc):
        with patch("shutil.which", return_value=None):
            with patch("runtime.mcp_client._user_script_dirs", return_value=[]):
                with patch("runtime.mcp_client._user_site_dirs", return_value=[]):
                    with pytest.raises(RuntimeError, match="init failed"):
                        client._ensure_process()
    # proc is terminated via _release_locked(proc)
    mock_proc.terminate.assert_called_once()
    assert mcp_client._PROC_INIT.get(client._key) is None


def test_release_locked_with_process(tmp_path: Path) -> None:
    _make_config_dir(tmp_path)
    client = McpClient("test", tmp_path)
    proc = MagicMock(spec=subprocess.Popen)
    proc.wait.return_value = 0
    mcp_client._PROC_POOL[client._key] = proc
    mcp_client._PROC_INIT[client._key] = True
    client._release_locked(proc)
    proc.terminate.assert_called_once()
    # _PROC_INIT is always cleared
    assert client._key not in mcp_client._PROC_INIT


def test_release_locked_wait_timeout_kills(tmp_path: Path) -> None:
    proc = MagicMock(spec=subprocess.Popen)
    proc.wait.side_effect = subprocess.TimeoutExpired("cmd", 2)
    client = McpClient("test", tmp_path)
    client._release_locked(proc)
    proc.kill.assert_called_once()


# ---------------------------------------------------------------------------
# call_tool
# ---------------------------------------------------------------------------


def test_call_tool_success(tmp_path: Path) -> None:
    _make_config_dir(tmp_path)
    client = McpClient("test", tmp_path)
    mock_proc = _mock_proc_with_io('{"jsonrpc":"2.0","result":{"output":"ok"}}\n')
    with patch("subprocess.Popen", return_value=mock_proc):
        with patch("shutil.which", return_value=None):
            with patch("runtime.mcp_client._user_script_dirs", return_value=[]):
                with patch("runtime.mcp_client._user_site_dirs", return_value=[]):
                    result = client.call_tool("my_tool", {"x": 1})
    assert result["ok"] is True
    assert result["result"]["output"] == "ok"


def test_call_tool_response_error(tmp_path: Path) -> None:
    _make_config_dir(tmp_path)
    client = McpClient("test", tmp_path)
    mock_proc = _mock_proc_with_io('{"jsonrpc":"2.0","error":"tool failed"}\n')
    with patch("subprocess.Popen", return_value=mock_proc):
        with patch("shutil.which", return_value=None):
            with patch("runtime.mcp_client._user_script_dirs", return_value=[]):
                with patch("runtime.mcp_client._user_site_dirs", return_value=[]):
                    result = client.call_tool("my_tool", {})
    assert result["ok"] is False
    assert result["error"] == "tool failed"


def test_call_tool_exception_releases_pool(tmp_path: Path) -> None:
    _make_config_dir(tmp_path)
    client = McpClient("test", tmp_path)
    mock_proc = MagicMock(spec=subprocess.Popen)
    mock_proc.stdin = None
    mock_proc.stdout = None
    mock_proc.poll.return_value = None
    with patch("subprocess.Popen", return_value=mock_proc):
        with patch("shutil.which", return_value=None):
            with patch("runtime.mcp_client._user_script_dirs", return_value=[]):
                with patch("runtime.mcp_client._user_site_dirs", return_value=[]):
                    result = client.call_tool("my_tool", {})
    assert result["ok"] is False
    assert "pipes" in result["error"]


# ---------------------------------------------------------------------------
# async_call_tool
# ---------------------------------------------------------------------------


def _make_async_proc(init_resp: bytes | None, call_resp: bytes | None):
    """Build a mock async subprocess with sync stdin.write and async stdin.drain."""
    proc = MagicMock()
    proc.stdin = MagicMock()
    proc.stdin.write = MagicMock()
    proc.stdin.drain = AsyncMock()
    proc.stdout = MagicMock()
    proc.stdout.readline = AsyncMock()
    proc.terminate = MagicMock()
    proc.kill = MagicMock()
    proc.wait = AsyncMock(return_value=0)
    proc.stdout.readline.side_effect = [init_resp, call_resp]
    return proc


def test_async_call_tool_success(tmp_path: Path) -> None:
    _make_config_dir(tmp_path)
    client = McpClient("test", tmp_path)
    proc = _make_async_proc(
        b'{"jsonrpc":"2.0","result":{}}',
        b'{"jsonrpc":"2.0","result":{"data":"ok"}}',
    )
    with patch("asyncio.create_subprocess_exec", return_value=proc):
        with patch("runtime.mcp_client._user_script_dirs", return_value=[]):
            with patch("runtime.mcp_client._user_site_dirs", return_value=[]):
                result = asyncio.run(client.async_call_tool("tool", {"x": 1}))
    assert result["ok"] is True
    assert result["result"]["data"] == "ok"


def test_async_call_tool_not_configured(tmp_path: Path) -> None:
    client = McpClient("missing", tmp_path)
    result = asyncio.run(client.async_call_tool("tool", {}))
    assert result["ok"] is False
    assert "not configured" in result["error"]


def test_async_call_tool_spawn_failure(tmp_path: Path) -> None:
    _make_config_dir(tmp_path)
    client = McpClient("test", tmp_path)
    with patch("asyncio.create_subprocess_exec", side_effect=OSError("nope")):
        with patch("runtime.mcp_client._user_script_dirs", return_value=[]):
            with patch("runtime.mcp_client._user_site_dirs", return_value=[]):
                result = asyncio.run(client.async_call_tool("tool", {}))
    assert result["ok"] is False
    assert "Failed to spawn" in result["error"]


def test_async_call_tool_init_closed_stdout(tmp_path: Path) -> None:
    _make_config_dir(tmp_path)
    client = McpClient("test", tmp_path)
    proc = _make_async_proc(b"", b'{"jsonrpc":"2.0","result":{}}')
    with patch("asyncio.create_subprocess_exec", return_value=proc):
        with patch("runtime.mcp_client._user_script_dirs", return_value=[]):
            with patch("runtime.mcp_client._user_site_dirs", return_value=[]):
                result = asyncio.run(client.async_call_tool("tool", {}))
    assert result["ok"] is False
    assert "closed stdout during init" in result["error"]


def test_async_call_tool_init_error(tmp_path: Path) -> None:
    _make_config_dir(tmp_path)
    client = McpClient("test", tmp_path)
    proc = _make_async_proc(
        b'{"jsonrpc":"2.0","error":"bad init"}',
        b'{"jsonrpc":"2.0","result":{}}',
    )
    with patch("asyncio.create_subprocess_exec", return_value=proc):
        with patch("runtime.mcp_client._user_script_dirs", return_value=[]):
            with patch("runtime.mcp_client._user_site_dirs", return_value=[]):
                result = asyncio.run(client.async_call_tool("tool", {}))
    assert result["ok"] is False
    assert result["error"] == "bad init"


def test_async_call_tool_call_closed_stdout(tmp_path: Path) -> None:
    _make_config_dir(tmp_path)
    client = McpClient("test", tmp_path)
    proc = _make_async_proc(
        b'{"jsonrpc":"2.0","result":{}}',
        b"",
    )
    with patch("asyncio.create_subprocess_exec", return_value=proc):
        with patch("runtime.mcp_client._user_script_dirs", return_value=[]):
            with patch("runtime.mcp_client._user_site_dirs", return_value=[]):
                result = asyncio.run(client.async_call_tool("tool", {}))
    assert result["ok"] is False
    assert "closed stdout" in result["error"]


def test_async_call_tool_timeout(tmp_path: Path) -> None:
    _make_config_dir(tmp_path)
    client = McpClient("test", tmp_path)
    proc = _make_async_proc(b'{"jsonrpc":"2.0","result":{}}', b'{"jsonrpc":"2.0","result":{}}')
    proc.stdout.readline.side_effect = asyncio.TimeoutError()

    async def fake_wait_for(coro, timeout=None):
        return await coro

    with patch("asyncio.create_subprocess_exec", return_value=proc):
        with patch("asyncio.wait_for", side_effect=fake_wait_for):
            with patch("runtime.mcp_client._user_script_dirs", return_value=[]):
                with patch("runtime.mcp_client._user_site_dirs", return_value=[]):
                    result = asyncio.run(client.async_call_tool("tool", {}))
    assert result["ok"] is False
    assert "timed out" in result["error"]


def test_async_call_tool_response_error(tmp_path: Path) -> None:
    _make_config_dir(tmp_path)
    client = McpClient("test", tmp_path)
    proc = _make_async_proc(
        b'{"jsonrpc":"2.0","result":{}}',
        b'{"jsonrpc":"2.0","error":"call failed"}',
    )
    with patch("asyncio.create_subprocess_exec", return_value=proc):
        with patch("runtime.mcp_client._user_script_dirs", return_value=[]):
            with patch("runtime.mcp_client._user_site_dirs", return_value=[]):
                result = asyncio.run(client.async_call_tool("tool", {}))
    assert result["ok"] is False
    assert result["error"] == "call failed"


def test_async_call_tool_generic_exception(tmp_path: Path) -> None:
    _make_config_dir(tmp_path)
    client = McpClient("test", tmp_path)
    proc = _make_async_proc(b'{"jsonrpc":"2.0","result":{}}', b'{"jsonrpc":"2.0","result":{}}')
    proc.stdout.readline.side_effect = ValueError("parse error")

    async def fake_wait_for(coro, timeout=None):
        return await coro

    with patch("asyncio.create_subprocess_exec", return_value=proc):
        with patch("asyncio.wait_for", side_effect=fake_wait_for):
            with patch("runtime.mcp_client._user_script_dirs", return_value=[]):
                with patch("runtime.mcp_client._user_site_dirs", return_value=[]):
                    result = asyncio.run(client.async_call_tool("tool", {}))
    assert result["ok"] is False
    assert "parse error" in result["error"]


def test_async_call_tool_wait_timeout_kills(tmp_path: Path) -> None:
    _make_config_dir(tmp_path)
    client = McpClient("test", tmp_path)
    proc = _make_async_proc(
        b'{"jsonrpc":"2.0","result":{}}',
        b'{"jsonrpc":"2.0","result":{"data":"ok"}}',
    )

    async def fake_wait_for(coro, timeout=None):
        if timeout == 2:
            coro.close()
            raise asyncio.TimeoutError()
        return await coro

    with patch("asyncio.create_subprocess_exec", return_value=proc):
        with patch("asyncio.wait_for", side_effect=fake_wait_for):
            with patch("runtime.mcp_client._user_script_dirs", return_value=[]):
                with patch("runtime.mcp_client._user_site_dirs", return_value=[]):
                    result = asyncio.run(client.async_call_tool("tool", {}))
    assert result["ok"] is True
    proc.kill.assert_called_once()


# ---------------------------------------------------------------------------
# Coverage gaps: lines 43, 82, 273
# ---------------------------------------------------------------------------


def test_load_secrets_once_no_env_file_anywhere(tmp_path: Path, monkeypatch) -> None:
    """Cover line 43: _load_secrets_once returns when no .env exists at any path."""
    monkeypatch.setenv("AGENT_OS_ROOT", str(tmp_path / "nonexistent"))
    mcp_client._SECRETS_LOADED = False
    # Monkeypatch __file__ so the fallback parent.parent has no .env
    fake_dir = tmp_path / "some_pkg"
    fake_dir.mkdir(parents=True)
    fake_file = fake_dir / "mcp_client.py"
    fake_file.write_text("# placeholder", encoding="utf-8")
    monkeypatch.setattr(mcp_client, "__file__", str(fake_file))
    mcp_client._load_secrets_once()
    assert mcp_client._SECRETS_LOADED is True


def test_user_script_dirs_userbase_dir_exists(tmp_path: Path) -> None:
    """Cover line 82: userbase Scripts dir is added when it exists on disk."""
    userbase = tmp_path / "userbase"
    (userbase / "Scripts").mkdir(parents=True)
    with patch("sysconfig.get_path", return_value=""):
        with patch("sysconfig.get_config_var", return_value=str(userbase)):
            result = mcp_client._user_script_dirs()
    assert any("Scripts" in d for d in result)


def test_call_tool_response_error_after_successful_init(tmp_path: Path) -> None:
    """Cover line 273: call_tool returns error when response has 'error' after successful init."""
    _make_config_dir(tmp_path)
    client = McpClient("test", tmp_path)
    proc = MagicMock(spec=subprocess.Popen)
    proc.stdin = MagicMock()
    proc.stdout = MagicMock()
    proc.poll.return_value = None
    # First readline: init success, second readline: call error
    proc.stdout.readline.side_effect = [
        '{"jsonrpc":"2.0","result":{}}\n',
        '{"jsonrpc":"2.0","error":"tool error"}\n',
    ]
    with patch("subprocess.Popen", return_value=proc):
        with patch("shutil.which", return_value=None):
            with patch("runtime.mcp_client._user_script_dirs", return_value=[]):
                with patch("runtime.mcp_client._user_site_dirs", return_value=[]):
                    result = client.call_tool("my_tool", {})
    assert result["ok"] is False
    assert result["error"] == "tool error"
