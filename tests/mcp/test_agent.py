#!/usr/bin/env python3
"""Tests for aizee_mcp.agent."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aizee_mcp.agent import McpAgent, Tool, ToolCall

# ---------------------------------------------------------------------------
# Existing tests (kept for regression)
# ---------------------------------------------------------------------------


def test_agent_registers_servers():
    agent = McpAgent("test")
    agent.register_server("mock", "python", args=["-m", "mock_server"])
    assert "mock" in agent.servers


def test_agent_starts_empty():
    agent = McpAgent()
    assert agent.list_tools() == []
    assert agent.find_tool("missing") is None


def test_tool_dataclass():
    t = Tool(name="read", server="mock", description="read file", input_schema={"type": "object"})
    assert t.name == "read"


# ---------------------------------------------------------------------------
# Helper: mock async context managers for stdio_client and ClientSession
# ---------------------------------------------------------------------------


def _mock_stdio_client():
    """Return a mock for stdio_client that works as an async context manager."""
    mock = MagicMock()
    mock.return_value.__aenter__ = AsyncMock(return_value=(MagicMock(), MagicMock()))
    mock.return_value.__aexit__ = AsyncMock(return_value=None)
    return mock


def _mock_client_session(session_mock):
    """Return a mock for ClientSession that works as an async context manager."""
    mock = MagicMock()
    mock.return_value.__aenter__ = AsyncMock(return_value=session_mock)
    mock.return_value.__aexit__ = AsyncMock(return_value=None)
    return mock


def _make_mock_session(tools=None, call_result=None):
    """Create a mock ClientSession with configurable tools and call_result."""
    session = MagicMock()
    session.initialize = AsyncMock()
    if tools is not None:
        session.list_tools = AsyncMock(return_value=MagicMock(tools=tools))
    if call_result is not None:
        session.call_tool = AsyncMock(return_value=call_result)
    return session


# ---------------------------------------------------------------------------
# register_server — unsafe command (line 64)
# ---------------------------------------------------------------------------


def test_register_server_unsafe_command_raises():
    """Cover line 64: command not in safe whitelist raises ValueError."""
    agent = McpAgent("test")
    with pytest.raises(ValueError, match="not in the safe-command whitelist"):
        agent.register_server("evil", "/bin/rm", args=["-rf", "/"])


def test_register_server_with_env():
    """Cover register_server with env parameter."""
    agent = McpAgent("test")
    agent.register_server("mock", "python", args=["-m", "server"], env={"API_KEY": "secret"})
    assert "mock" in agent.servers
    assert agent.servers["mock"].env == {"API_KEY": "secret"}


def test_register_server_node_command():
    """Cover register_server with node command (in safe whitelist)."""
    agent = McpAgent("test")
    agent.register_server("node-server", "node", args=["server.js"])
    assert "node-server" in agent.servers


# ---------------------------------------------------------------------------
# discover_tools (lines 76-91)
# ---------------------------------------------------------------------------


def test_discover_tools_finds_tools():
    """Cover lines 76-91: discover_tools returns tools from registered servers."""
    agent = McpAgent("test")
    agent.register_server("mock", "python", args=["-m", "mock_server"])

    mock_tool = MagicMock()
    mock_tool.name = "read_file"
    mock_tool.description = "Read a file"
    mock_tool.inputSchema = {"type": "object", "properties": {"path": {"type": "string"}}}

    session = _make_mock_session(tools=[mock_tool])
    stdio_mock = _mock_stdio_client()
    session_mock = _mock_client_session(session)

    with patch("aizee_mcp.agent.stdio_client", stdio_mock), \
         patch("aizee_mcp.agent.ClientSession", session_mock):
        tools = asyncio.run(agent.discover_tools())

    assert len(tools) == 1
    assert tools[0].name == "read_file"
    assert tools[0].server == "mock"
    assert tools[0].description == "Read a file"
    assert tools[0].input_schema == {"type": "object", "properties": {"path": {"type": "string"}}}
    # Tools should be stored on the agent
    assert agent.list_tools() == tools


def test_discover_tools_empty_server():
    """Cover lines 76-91: discover_tools with no tools returned."""
    agent = McpAgent("test")
    agent.register_server("mock", "python", args=["-m", "mock_server"])

    session = _make_mock_session(tools=[])
    stdio_mock = _mock_stdio_client()
    session_mock = _mock_client_session(session)

    with patch("aizee_mcp.agent.stdio_client", stdio_mock), \
         patch("aizee_mcp.agent.ClientSession", session_mock):
        tools = asyncio.run(agent.discover_tools())

    assert tools == []


def test_discover_tools_multiple_servers():
    """Cover lines 76-91: discover_tools from multiple servers."""
    agent = McpAgent("test")
    agent.register_server("server1", "python", args=["-m", "s1"])
    agent.register_server("server2", "node", args=["s2.js"])

    tool1 = MagicMock()
    tool1.name = "read"
    tool1.description = "read"
    tool1.inputSchema = {}

    tool2 = MagicMock()
    tool2.name = "write"
    tool2.description = "write"
    tool2.inputSchema = {}

    session1 = _make_mock_session(tools=[tool1])
    session2 = _make_mock_session(tools=[tool2])

    # Each call to ClientSession should return a different session
    session_mock = MagicMock()
    session_mock.return_value.__aenter__ = AsyncMock(side_effect=[session1, session2])
    session_mock.return_value.__aexit__ = AsyncMock(return_value=None)

    stdio_mock = _mock_stdio_client()

    with patch("aizee_mcp.agent.stdio_client", stdio_mock), \
         patch("aizee_mcp.agent.ClientSession", session_mock):
        tools = asyncio.run(agent.discover_tools())

    assert len(tools) == 2
    names = {t.name for t in tools}
    assert names == {"read", "write"}


# ---------------------------------------------------------------------------
# find_tool (lines 98-99)
# ---------------------------------------------------------------------------


def test_find_tool_existing():
    """Cover lines 98-99: find_tool returns the matching tool."""
    agent = McpAgent("test")
    tool = Tool(name="read", server="mock", description="read file")
    agent._tools = [tool]
    found = agent.find_tool("read")
    assert found is tool


def test_find_tool_missing():
    """Cover lines 98-99: find_tool returns None for missing tool."""
    agent = McpAgent("test")
    agent._tools = [Tool(name="read", server="mock")]
    found = agent.find_tool("write")
    assert found is None


# ---------------------------------------------------------------------------
# call_tool (lines 108-133)
# ---------------------------------------------------------------------------


def test_call_tool_whitelist_rejects():
    """Cover lines 108-115: tool not in allowed_tools whitelist."""
    agent = McpAgent("test")
    agent.allowed_tools = {"read"}
    agent._tools = [Tool(name="read", server="mock")]

    call = asyncio.run(agent.call_tool("write", {"data": "test"}))
    assert call.tool == "write"
    assert "not in the allowed_tools whitelist" in call.error
    assert len(agent._history) == 1


def test_call_tool_not_found():
    """Cover lines 117-121: tool not found in registered tools."""
    agent = McpAgent("test")
    agent._tools = []

    call = asyncio.run(agent.call_tool("missing_tool", {"arg": "val"}))
    assert call.tool == "missing_tool"
    assert "not found" in call.error
    assert len(agent._history) == 1


def test_call_tool_success():
    """Cover lines 123-133: successful tool call returns result."""
    agent = McpAgent("test")
    agent.register_server("mock", "python", args=["-m", "mock_server"])
    agent._tools = [Tool(name="read", server="mock")]

    # Mock the call_tool response
    mock_content = MagicMock()
    mock_content.text = "file contents here"
    mock_result = MagicMock()
    mock_result.content = [mock_content]

    session = _make_mock_session(call_result=mock_result)
    stdio_mock = _mock_stdio_client()
    session_mock = _mock_client_session(session)

    with patch("aizee_mcp.agent.stdio_client", stdio_mock), \
         patch("aizee_mcp.agent.ClientSession", session_mock):
        call = asyncio.run(agent.call_tool("read", {"path": "/tmp/test.txt"}))

    assert call.tool == "read"
    assert call.error == ""
    assert call.result == ["file contents here"]
    assert len(agent._history) == 1


def test_call_tool_success_no_content():
    """Cover line 130: result with no content returns None."""
    agent = McpAgent("test")
    agent.register_server("mock", "python", args=["-m", "mock_server"])
    agent._tools = [Tool(name="read", server="mock")]

    mock_result = MagicMock()
    mock_result.content = None

    session = _make_mock_session(call_result=mock_result)
    stdio_mock = _mock_stdio_client()
    session_mock = _mock_client_session(session)

    with patch("aizee_mcp.agent.stdio_client", stdio_mock), \
         patch("aizee_mcp.agent.ClientSession", session_mock):
        call = asyncio.run(agent.call_tool("read", {"path": "/tmp/test.txt"}))

    assert call.tool == "read"
    assert call.result is None


def test_call_tool_whitelist_allows():
    """Cover lines 108-115: tool in allowed_tools whitelist is allowed."""
    agent = McpAgent("test")
    agent.allowed_tools = {"read"}
    agent.register_server("mock", "python", args=["-m", "mock_server"])
    agent._tools = [Tool(name="read", server="mock")]

    mock_content = MagicMock()
    mock_content.text = "ok"
    mock_result = MagicMock()
    mock_result.content = [mock_content]

    session = _make_mock_session(call_result=mock_result)
    stdio_mock = _mock_stdio_client()
    session_mock = _mock_client_session(session)

    with patch("aizee_mcp.agent.stdio_client", stdio_mock), \
         patch("aizee_mcp.agent.ClientSession", session_mock):
        call = asyncio.run(agent.call_tool("read", {}))

    assert call.error == ""
    assert call.result == ["ok"]


# ---------------------------------------------------------------------------
# run_task (lines 137-145)
# ---------------------------------------------------------------------------


def test_run_task_no_tools_breaks_immediately():
    """Cover lines 137-145: run_task breaks when no tools registered."""
    agent = McpAgent("test")
    calls = asyncio.run(agent.run_task("do something"))
    assert calls == []


def test_run_task_success_first_call():
    """Cover lines 137-145: run_task succeeds on first call (no error)."""
    agent = McpAgent("test")
    agent._tools = [Tool(name="read", server="mock")]

    with patch.object(agent, "call_tool", AsyncMock(return_value=ToolCall(tool="read", result="ok"))):
        calls = asyncio.run(agent.run_task("do something"))
        assert len(calls) == 1
        assert calls[0].tool == "read"
        assert calls[0].error == ""


def test_run_task_retries_on_error():
    """Cover lines 137-145: run_task retries when call has error."""
    agent = McpAgent("test")
    agent._tools = [Tool(name="read", server="mock")]

    error_call = ToolCall(tool="read", error="failed")
    success_call = ToolCall(tool="read", result="ok")

    with patch.object(agent, "call_tool", AsyncMock(side_effect=[error_call, success_call])):
        calls = asyncio.run(agent.run_task("do something", steps=5))
        assert len(calls) == 2
        assert calls[0].error == "failed"
        assert calls[1].error == ""


def test_run_task_exhausts_steps():
    """Cover lines 137-145: run_task exhausts all steps on persistent error."""
    agent = McpAgent("test")
    agent._tools = [Tool(name="read", server="mock")]

    error_call = ToolCall(tool="read", error="always fails")

    with patch.object(agent, "call_tool", AsyncMock(return_value=error_call)):
        calls = asyncio.run(agent.run_task("do something", steps=3))
        assert len(calls) == 3
        assert all(c.error == "always fails" for c in calls)
