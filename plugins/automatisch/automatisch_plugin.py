#!/usr/bin/env python3
"""AutomatischPlugin for aiZee — proxies to external MCP server.

External MCP server: npx -y @automatisch/mcp
Required env vars: AUTOMATISCH_API_KEY, AUTOMATISCH_URL
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from runtime.mcp_client import McpClient
from runtime.plugin import AIOSPlugin


class AutomatischPlugin(AIOSPlugin):
    """Bridge AIOS kernel to the external automatisch MCP server."""

    name = "automatisch"
    version = "0.1.0"

    def on_load(self) -> None:
        """Validate required env vars on plugin load."""
        import os
        missing = [v for v in ("AUTOMATISCH_API_KEY", "AUTOMATISCH_URL") if not os.environ.get(v)]
        if missing:
            import logging
            logging.getLogger(__name__).warning(
                "%s plugin loaded without %s — tool calls will fail until set",
                self.__class__.__name__, ", ".join(missing),
            )

    def _client(self) -> McpClient:
        return McpClient("automatisch", self.kernel.root)

    def _proxy(self, tool: str, arguments: dict[str, Any]) -> str:
        """Call a tool on the external MCP server via stdio."""
        try:
            result = self._client().call_tool(tool, arguments)
            return result if isinstance(result, str) else json.dumps(result, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": "AutomatischPlugin MCP call failed: " + str(exc)})

    def automatisch_list_flows(self) -> str:
        """List flows (free-first)."""
        return self._proxy("list_flows", {})

    def automatisch_get_flow(self, flow_id: str) -> str:
        """Get a flow."""
        return self._proxy("get_flow", {"flow_id": flow_id})

    def automatisch_create_flow(self, name: str, trigger: str) -> str:
        """Create a flow."""
        return self._proxy("create_flow", {"name": name, "trigger": trigger})

    def automatisch_list_executions(self, limit: int = 10) -> str:
        """List executions."""
        return self._proxy("list_executions", {"limit": limit})

    def automatisch_get_execution(self, execution_id: str) -> str:
        """Get an execution."""
        return self._proxy("get_execution", {"execution_id": execution_id})

    def automatisch_list_credentials(self) -> str:
        """List credentials."""
        return self._proxy("list_credentials", {})

    def register_mcp_tools(self) -> list[Callable[..., str]]:
        return [
            self.automatisch_list_flows,
            self.automatisch_get_flow,
            self.automatisch_create_flow,
            self.automatisch_list_executions,
            self.automatisch_get_execution,
            self.automatisch_list_credentials
        ]
