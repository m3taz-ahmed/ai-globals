#!/usr/bin/env python3
"""MCP agent loop and multi-server routing for aiZee.

Re-implements the mcp-agent pattern: an agent that can discover and call tools
across multiple MCP servers, maintain an event loop, and collect results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@dataclass
class Tool:
    """A tool discovered from an MCP server."""

    name: str
    server: str
    description: str = ""
    input_schema: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolCall:
    """A tool call request or result."""

    tool: str
    arguments: dict[str, Any] = field(default_factory=dict)
    result: Any = None
    error: str = ""


class McpAgent:
    """Lightweight MCP agent that routes calls across servers.

    Security: Only tools in the allowed_tools whitelist (if set) can be called.
    Server registration validates command against a safe-command list.
    """

    # Whitelist of safe commands for server registration
    _SAFE_COMMANDS: ClassVar[set[str]] = {"python", "npx", "uvx", "node"}

    def __init__(self, name: str = "aios-agent") -> None:
        self.name = name
        self.servers: dict[str, StdioServerParameters] = {}
        self._tools: list[Tool] = []
        self._history: list[ToolCall] = []
        self.allowed_tools: set[str] | None = None  # None = all allowed (no whitelist)

    def register_server(self, name: str, command: str, args: list[str] | None = None, env: dict[str, str] | None = None) -> None:
        """Register an MCP server to be connected at runtime.

        Security: command must be in the safe-command whitelist.
        """
        # Extract the base command (strip path)
        import os

        base_cmd = os.path.basename(command)
        if base_cmd not in self._SAFE_COMMANDS:
            raise ValueError(
                f"Command '{command}' is not in the safe-command whitelist: {self._SAFE_COMMANDS}. "
                "Add it to McpAgent._SAFE_COMMANDS if trusted."
            )
        self.servers[name] = StdioServerParameters(
            command=command,
            args=args or [],
            env=env,
        )

    async def discover_tools(self) -> list[Tool]:
        """Discover tools from all registered servers."""
        tools: list[Tool] = []
        for server_name, params in self.servers.items():
            async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
                await session.initialize()
                response = await session.list_tools()
                for tool in response.tools:
                    tools.append(
                        Tool(
                            name=tool.name,
                            server=server_name,
                            description=tool.description or "",
                            input_schema=tool.inputSchema or {},
                        )
                    )
        self._tools = tools
        return tools

    def list_tools(self) -> list[Tool]:
        return self._tools

    def find_tool(self, name: str) -> Tool | None:
        for tool in self._tools:
            if tool.name == name:
                return tool
        return None

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> ToolCall:
        """Call a tool by name on the server that owns it.

        Security: If allowed_tools whitelist is set, only those tools can be called.
        """
        # Check whitelist if configured
        if self.allowed_tools is not None and name not in self.allowed_tools:
            call = ToolCall(
                tool=name,
                arguments=arguments,
                error=f"Tool {name!r} is not in the allowed_tools whitelist",
            )
            self._history.append(call)
            return call

        tool = self.find_tool(name)
        if not tool:
            call = ToolCall(tool=name, arguments=arguments, error=f"Tool {name!r} not found")
            self._history.append(call)
            return call

        params = self.servers[tool.server]
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(name, arguments=arguments)
            call = ToolCall(
                tool=name,
                arguments=arguments,
                result=[c.text for c in result.content if hasattr(c, "text")] if result.content else None,
            )
            self._history.append(call)
            return call

    async def run_task(self, task: str, steps: int = 10) -> list[ToolCall]:
        """Run a simple task loop (placeholder; real driver is an LLM planner)."""
        calls: list[ToolCall] = []
        for _ in range(steps):
            if not self._tools:
                break
            call = await self.call_tool(self._tools[0].name, {"task": task})
            calls.append(call)
            if not call.error:
                break
        return calls
