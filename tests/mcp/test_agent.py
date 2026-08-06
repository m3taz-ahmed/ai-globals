#!/usr/bin/env python3
"""Tests for aios_mcp.agent."""

from __future__ import annotations

from aios_mcp.agent import McpAgent, Tool


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
