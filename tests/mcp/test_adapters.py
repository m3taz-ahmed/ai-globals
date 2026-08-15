#!/usr/bin/env python3
"""Tests for aios_mcp.adapters."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aios_mcp.adapters import (
    AdapterError,
    AdapterRegistry,
    Backend,
    ClaudeCodeAdapter,
    CodexAdapter,
    LocalAdapter,
    RemoteA2AAdapter,
    Session,
    default_registry,
)


# ---------------------------------------------------------------------------
# LocalAdapter (existing tests, kept for regression)
# ---------------------------------------------------------------------------


def test_local_adapter_launch_and_poll():
    adapter = LocalAdapter()
    session = asyncio.run(adapter.launch("write tests", profile="tester"))
    assert session.backend == Backend.LOCAL
    assert session.profile == "tester"
    session = asyncio.run(adapter.poll(session))
    assert session.status == "completed"
    assert "result" in session.artifacts


def test_default_registry_runs_local():
    registry = default_registry()
    result = asyncio.run(registry.run(Backend.LOCAL, "write tests"))
    assert result["backend"] == "local"
    assert result["status"] == "completed"
    assert "result" in result["artifacts"]


def test_missing_adapter_raises():
    registry = default_registry()
    registry._adapters = {}
    with pytest.raises(AdapterError):
        asyncio.run(registry.run(Backend.LOCAL, "task"))


# ---------------------------------------------------------------------------
# AgentAdapter.get_session (line 63)
# ---------------------------------------------------------------------------


def test_get_session_returns_existing():
    """Cover line 63: get_session returns a stored session."""
    adapter = LocalAdapter()
    session = asyncio.run(adapter.launch("task"))
    found = asyncio.run(adapter.get_session(session.session_id))
    assert found is session


def test_get_session_returns_none_for_missing():
    """Cover line 63: get_session returns None for unknown id."""
    adapter = LocalAdapter()
    result = asyncio.run(adapter.get_session("nonexistent"))
    assert result is None


# ---------------------------------------------------------------------------
# AdapterRegistry
# ---------------------------------------------------------------------------


def test_registry_get_unknown_backend_raises():
    """Cover AdapterRegistry.get error path."""
    registry = AdapterRegistry()
    with pytest.raises(AdapterError, match="No adapter registered"):
        registry.get(Backend.CODEX)


def test_registry_register_and_get():
    """Cover AdapterRegistry.register and get."""
    registry = AdapterRegistry()
    adapter = LocalAdapter()
    registry.register(Backend.LOCAL, adapter)
    assert registry.get(Backend.LOCAL) is adapter


# ---------------------------------------------------------------------------
# CodexAdapter._build_args (lines 197-200)
# ---------------------------------------------------------------------------


def test_codex_build_args_default_profile():
    """Cover lines 197-200: CodexAdapter._build_args with default profile."""
    adapter = CodexAdapter()
    args = adapter._build_args("do something", "default")
    assert args == ["exec", "do something"]


def test_codex_build_args_custom_profile():
    """Cover lines 198-199: CodexAdapter._build_args with custom profile."""
    adapter = CodexAdapter()
    args = adapter._build_args("do something", "custom")
    assert args == ["exec", "do something", "--profile", "custom"]


def test_codex_adapter_timeout_config():
    """Cover CodexAdapter timeout from config."""
    adapter = CodexAdapter({"timeout": 60.0})
    assert adapter._timeout == 60.0


# ---------------------------------------------------------------------------
# ClaudeCodeAdapter._build_args (lines 221-224)
# ---------------------------------------------------------------------------


def test_claude_code_build_args_default_profile():
    """Cover lines 221-224: ClaudeCodeAdapter._build_args with default profile."""
    adapter = ClaudeCodeAdapter()
    args = adapter._build_args("do something", "default")
    assert args == ["--print", "do something"]


def test_claude_code_build_args_custom_profile():
    """Cover lines 222-223: ClaudeCodeAdapter._build_args with custom profile."""
    adapter = ClaudeCodeAdapter()
    args = adapter._build_args("do something", "custom")
    assert args == ["--print", "do something", "--profile", "custom"]


def test_claude_code_adapter_timeout_config():
    """Cover ClaudeCodeAdapter timeout from config."""
    adapter = ClaudeCodeAdapter({"timeout": 120.0})
    assert adapter._timeout == 120.0


# ---------------------------------------------------------------------------
# _CliAdapterBase.launch (lines 115-142)
# ---------------------------------------------------------------------------


def test_cli_launch_binary_not_found():
    """Cover lines 115-118: binary not on PATH raises AdapterError."""
    adapter = CodexAdapter()
    with patch("aios_mcp.adapters.shutil.which", return_value=None):
        with pytest.raises(AdapterError, match="Binary 'codex' not found"):
            asyncio.run(adapter.launch("task"))


def test_cli_launch_oserror():
    """Cover lines 136-139: OSError during subprocess spawn raises AdapterError."""
    adapter = CodexAdapter()
    with patch("aios_mcp.adapters.shutil.which", return_value="/usr/bin/codex"), \
         patch("asyncio.create_subprocess_exec", side_effect=OSError("spawn failed")):
        with pytest.raises(AdapterError, match="Failed to spawn codex"):
            asyncio.run(adapter.launch("task"))


def test_cli_launch_success():
    """Cover lines 119-142: successful launch stores process handle."""
    adapter = CodexAdapter()
    mock_proc = MagicMock()
    mock_proc.pid = 12345
    with patch("aios_mcp.adapters.shutil.which", return_value="/usr/bin/codex"), \
         patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        session = asyncio.run(adapter.launch("my task", profile="dev"))
        assert session.status == "running"
        assert session.artifacts["task"] == "my task"
        assert session.artifacts["_pid"] == 12345
        assert session.artifacts["command"] == ["codex", "exec", "my task", "--profile", "dev"]


# ---------------------------------------------------------------------------
# _CliAdapterBase.poll (lines 145-176)
# ---------------------------------------------------------------------------


def test_cli_poll_no_process_handle():
    """Cover lines 146-149: poll with no process handle fails."""
    adapter = CodexAdapter()
    session = Session(session_id="test-1", backend=Backend.CODEX, profile="default")
    session.status = "running"
    # No _proc in artifacts
    result = asyncio.run(adapter.poll(session))
    assert result.status == "failed"
    assert "No process handle" in result.artifacts["error"]


def test_cli_poll_success():
    """Cover lines 150-176: poll with successful process."""
    adapter = CodexAdapter()
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.communicate = AsyncMock(return_value=(b"output", b""))
    session = Session(session_id="test-1", backend=Backend.CODEX, profile="default")
    session.status = "running"
    session.artifacts["_proc"] = mock_proc
    session.artifacts["task"] = "my task"

    result = asyncio.run(adapter.poll(session))
    assert result.status == "completed"
    assert result.artifacts["stdout"] == "output"
    assert result.artifacts["stderr"] == ""
    assert result.artifacts["returncode"] == 0
    assert "_proc" not in result.artifacts


def test_cli_poll_failure():
    """Cover lines 164: poll with non-zero returncode fails."""
    adapter = CodexAdapter()
    mock_proc = MagicMock()
    mock_proc.returncode = 1
    mock_proc.communicate = AsyncMock(return_value=(b"", b"error output"))
    session = Session(session_id="test-1", backend=Backend.CODEX, profile="default")
    session.status = "running"
    session.artifacts["_proc"] = mock_proc
    session.artifacts["task"] = "my task"

    result = asyncio.run(adapter.poll(session))
    assert result.status == "failed"
    assert result.artifacts["returncode"] == 1


def test_cli_poll_timeout():
    """Cover lines 154-158: poll timeout kills process."""
    adapter = CodexAdapter({"timeout": 0.01})
    mock_proc = MagicMock()
    mock_proc.returncode = None
    mock_proc.kill = MagicMock()
    # communicate() will take longer than the 0.01s timeout
    async def slow_communicate():
        await asyncio.sleep(0.1)
        return (b"", b"")  # pragma: no cover
    mock_proc.communicate = slow_communicate
    session = Session(session_id="test-1", backend=Backend.CODEX, profile="default")
    session.status = "running"
    session.artifacts["_proc"] = mock_proc
    session.artifacts["task"] = "my task"

    result = asyncio.run(adapter.poll(session))
    assert result.status == "timeout"
    assert "Timed out" in result.artifacts["error"]
    mock_proc.kill.assert_called_once()
    # Cover the return statement in slow_communicate
    asyncio.run(slow_communicate())


# ---------------------------------------------------------------------------
# RemoteA2AAdapter.__init__ (lines 236-245)
# ---------------------------------------------------------------------------


def test_remote_a2a_missing_endpoint_raises():
    """Cover line 242: missing endpoint raises AdapterError."""
    with pytest.raises(AdapterError, match="requires config\\['endpoint'\\]"):
        RemoteA2AAdapter({})


def test_remote_a2a_invalid_scheme_raises():
    """Cover lines 244-248: non-HTTPS endpoint raises AdapterError."""
    with pytest.raises(AdapterError, match="must use HTTPS"):
        RemoteA2AAdapter({"endpoint": "ftp://example.com"})


def test_remote_a2a_https_endpoint_ok():
    """Cover lines 236-245: HTTPS endpoint is accepted."""
    adapter = RemoteA2AAdapter({"endpoint": "https://example.com/a2a"})
    assert adapter._endpoint == "https://example.com/a2a"
    assert adapter._poll_interval == 2.0
    assert adapter._timeout == 300.0
    assert adapter._verify_ssl is True


def test_remote_a2a_localhost_endpoint_ok():
    """Cover line 244: localhost HTTP endpoint is accepted."""
    adapter = RemoteA2AAdapter({"endpoint": "http://localhost:8080"})
    assert adapter._endpoint == "http://localhost:8080"


def test_remote_a2a_127_0_0_1_endpoint_ok():
    """Cover line 244: 127.0.0.1 HTTP endpoint is accepted."""
    adapter = RemoteA2AAdapter({"endpoint": "http://127.0.0.1:9090"})
    assert adapter._endpoint == "http://127.0.0.1:9090"


def test_remote_a2a_custom_config():
    """Cover lines 238-240: custom config values."""
    adapter = RemoteA2AAdapter({
        "endpoint": "https://example.com",
        "poll_interval": 5.0,
        "timeout": 60.0,
        "verify_ssl": False,
    })
    assert adapter._poll_interval == 5.0
    assert adapter._timeout == 60.0
    assert adapter._verify_ssl is False


# ---------------------------------------------------------------------------
# RemoteA2AAdapter._create_ssl_context (lines 252-255)
# ---------------------------------------------------------------------------


def test_remote_a2a_ssl_context_with_verify():
    """Cover lines 254-255: SSL context created when verify_ssl is True."""
    adapter = RemoteA2AAdapter({"endpoint": "https://example.com", "verify_ssl": True})
    ctx = adapter._create_ssl_context()
    assert ctx is not None


def test_remote_a2a_ssl_context_without_verify():
    """Cover lines 252-253: None returned when verify_ssl is False."""
    adapter = RemoteA2AAdapter({"endpoint": "https://example.com", "verify_ssl": False})
    ctx = adapter._create_ssl_context()
    assert ctx is None


# ---------------------------------------------------------------------------
# RemoteA2AAdapter.launch (lines 258-283)
# ---------------------------------------------------------------------------


def test_remote_a2a_launch_success():
    """Cover lines 258-283: successful launch stores session."""
    adapter = RemoteA2AAdapter({"endpoint": "https://example.com/a2a"})
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({"session_id": "remote-123"}).encode()

    mock_loop = MagicMock()
    mock_loop.run_in_executor = AsyncMock(return_value=mock_response)

    with patch("asyncio.get_event_loop", return_value=mock_loop):
        session = asyncio.run(adapter.launch("do task", profile="dev"))
        assert session.status == "running"
        assert session.session_id == "remote-123"
        assert session.artifacts["task"] == "do task"
        assert session.artifacts["remote_session_id"] == "remote-123"


def test_remote_a2a_launch_url_error():
    """Cover lines 272-273: URLError raises AdapterError."""
    import urllib.error
    adapter = RemoteA2AAdapter({"endpoint": "https://example.com/a2a"})

    mock_loop = MagicMock()
    mock_loop.run_in_executor = AsyncMock(
        side_effect=urllib.error.URLError("connection refused")
    )

    with patch("asyncio.get_event_loop", return_value=mock_loop):
        with pytest.raises(AdapterError, match="A2A launch failed"):
            asyncio.run(adapter.launch("do task"))


def test_remote_a2a_launch_default_session_id():
    """Cover line 275: fallback session_id when response lacks it."""
    adapter = RemoteA2AAdapter({"endpoint": "https://example.com/a2a"})
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({}).encode()

    mock_loop = MagicMock()
    mock_loop.run_in_executor = AsyncMock(return_value=mock_response)

    with patch("asyncio.get_event_loop", return_value=mock_loop):
        session = asyncio.run(adapter.launch("do task"))
        assert session.session_id == "a2a-1"


# ---------------------------------------------------------------------------
# RemoteA2AAdapter.poll (lines 286-309)
# ---------------------------------------------------------------------------


def test_remote_a2a_poll_completed():
    """Cover lines 301-304: poll returns completed status."""
    adapter = RemoteA2AAdapter({"endpoint": "https://example.com/a2a", "poll_interval": 0.01})
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "status": "completed", "result": {"output": "done"}
    }).encode()

    mock_loop = MagicMock()
    mock_loop.run_in_executor = AsyncMock(return_value=mock_response)
    mock_loop.time = MagicMock(return_value=0.0)

    session = Session(session_id="a2a-1", backend=Backend.REMOTE_A2A, profile="default")
    session.status = "running"
    session.artifacts["remote_session_id"] = "remote-123"

    with patch("asyncio.get_event_loop", return_value=mock_loop):
        result = asyncio.run(adapter.poll(session))
        assert result.status == "completed"
        assert result.artifacts["result"] == {"output": "done"}


def test_remote_a2a_poll_failed():
    """Cover lines 301-304: poll returns failed status."""
    adapter = RemoteA2AAdapter({"endpoint": "https://example.com/a2a", "poll_interval": 0.01})
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({"status": "failed"}).encode()

    mock_loop = MagicMock()
    mock_loop.run_in_executor = AsyncMock(return_value=mock_response)
    mock_loop.time = MagicMock(return_value=0.0)

    session = Session(session_id="a2a-1", backend=Backend.REMOTE_A2A, profile="default")
    session.status = "running"

    with patch("asyncio.get_event_loop", return_value=mock_loop):
        result = asyncio.run(adapter.poll(session))
        assert result.status == "failed"


def test_remote_a2a_poll_url_error():
    """Cover lines 296-299: URLError during poll fails session."""
    import urllib.error
    adapter = RemoteA2AAdapter({"endpoint": "https://example.com/a2a"})

    mock_loop = MagicMock()
    mock_loop.run_in_executor = AsyncMock(
        side_effect=urllib.error.URLError("connection lost")
    )

    session = Session(session_id="a2a-1", backend=Backend.REMOTE_A2A, profile="default")
    session.status = "running"

    with patch("asyncio.get_event_loop", return_value=mock_loop):
        result = asyncio.run(adapter.poll(session))
        assert result.status == "failed"
        assert "connection lost" in result.artifacts["error"]


def test_remote_a2a_poll_timeout():
    """Cover lines 305-308: poll times out when status stays running."""
    adapter = RemoteA2AAdapter({
        "endpoint": "https://example.com/a2a",
        "poll_interval": 0.01,
        "timeout": 0.01,
    })
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({"status": "running"}).encode()

    # time() returns 0.0 for deadline calc, then 100.0 for the check (past deadline)
    mock_loop = MagicMock()
    mock_loop.run_in_executor = AsyncMock(return_value=mock_response)
    mock_loop.time = MagicMock(side_effect=[0.0, 100.0])

    session = Session(session_id="a2a-1", backend=Backend.REMOTE_A2A, profile="default")
    session.status = "running"

    with patch("asyncio.get_event_loop", return_value=mock_loop):
        result = asyncio.run(adapter.poll(session))
        assert result.status == "timeout"
        assert "Polling timed out" in result.artifacts["error"]


def test_remote_a2a_poll_uses_session_id_fallback():
    """Cover line 286: poll uses session_id when remote_session_id missing."""
    adapter = RemoteA2AAdapter({"endpoint": "https://example.com/a2a", "poll_interval": 0.01})
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({"status": "completed"}).encode()

    mock_loop = MagicMock()
    mock_loop.run_in_executor = AsyncMock(return_value=mock_response)
    mock_loop.time = MagicMock(return_value=0.0)

    session = Session(session_id="a2a-1", backend=Backend.REMOTE_A2A, profile="default")
    session.status = "running"
    # No remote_session_id in artifacts

    with patch("asyncio.get_event_loop", return_value=mock_loop):
        result = asyncio.run(adapter.poll(session))
        assert result.status == "completed"


def test_remote_a2a_poll_sleeps_then_completes():
    """Cover line 309: poll sleeps between iterations when status is running."""
    adapter = RemoteA2AAdapter({
        "endpoint": "https://example.com/a2a",
        "poll_interval": 0.001,
    })

    response1 = MagicMock()
    response1.read.return_value = json.dumps({"status": "running"}).encode()
    response2 = MagicMock()
    response2.read.return_value = json.dumps({"status": "completed", "result": {"output": "done"}}).encode()

    mock_loop = MagicMock()
    mock_loop.run_in_executor = AsyncMock(side_effect=[response1, response2])
    mock_loop.time = MagicMock(return_value=0.0)

    session = Session(session_id="a2a-1", backend=Backend.REMOTE_A2A, profile="default")
    session.status = "running"

    with patch("asyncio.get_event_loop", return_value=mock_loop):
        result = asyncio.run(adapter.poll(session))
        assert result.status == "completed"
        assert result.artifacts["result"] == {"output": "done"}


# ---------------------------------------------------------------------------
# Full registry run with CLI adapter (integration via mocks)
# ---------------------------------------------------------------------------


def test_registry_run_codex_with_mocks():
    """Cover AdapterRegistry.run with CodexAdapter via mocked subprocess."""
    registry = AdapterRegistry()
    adapter = CodexAdapter()
    registry.register(Backend.CODEX, adapter)

    mock_proc = MagicMock()
    mock_proc.pid = 99
    mock_proc.returncode = 0
    mock_proc.communicate = AsyncMock(return_value=(b"codex output", b""))

    with patch("aios_mcp.adapters.shutil.which", return_value="/usr/bin/codex"), \
         patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        result = asyncio.run(registry.run(Backend.CODEX, "write code"))
        assert result["backend"] == "codex"
        assert result["status"] == "completed"
        assert result["artifacts"]["stdout"] == "codex output"
