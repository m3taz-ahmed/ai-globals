#!/usr/bin/env python3
"""N8nPlugin for aiZee — proxies to external MCP server.

External MCP server: npx -y @n8n/mcp
Required env vars: N8N_API_KEY, N8N_BASE_URL
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from runtime.mcp_client import McpClient
from runtime.plugin import AIOSPlugin


class N8nPlugin(AIOSPlugin):
    """Bridge AIOS kernel to the external n8n MCP server."""

    name = "n8n"
    version = "0.1.0"

    def on_load(self) -> None:
        """Validate required env vars on plugin load."""
        import os
        missing = [v for v in ("N8N_API_KEY", "N8N_BASE_URL") if not os.environ.get(v)]
        if missing:
            import logging
            logging.getLogger(__name__).warning(
                "%s plugin loaded without %s — tool calls will fail until set",
                self.__class__.__name__, ", ".join(missing),
            )

    def _client(self) -> McpClient:
        return McpClient("n8n", self.kernel.root)

    def _proxy(self, tool: str, arguments: dict[str, Any]) -> str:
        """Call a tool on the external MCP server via stdio."""
        try:
            result = self._client().call_tool(tool, arguments)
            return result if isinstance(result, str) else json.dumps(result, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": "N8nPlugin MCP call failed: " + str(exc)})

    def n8n_list_workflows(self) -> str:
        """List workflows (fair-code)."""
        return self._proxy("list_workflows", {})

    def n8n_get_workflow(self, workflow_id: str) -> str:
        """Get a workflow."""
        return self._proxy("get_workflow", {"workflow_id": workflow_id})

    def n8n_create_workflow(self, name: str, nodes: str) -> str:
        """Create a workflow."""
        return self._proxy("create_workflow", {"name": name, "nodes": nodes})

    def n8n_execute_workflow(self, workflow_id: str) -> str:
        """Execute a workflow."""
        return self._proxy("execute_workflow", {"workflow_id": workflow_id})

    def n8n_list_executions(self, limit: int = 10) -> str:
        """List executions."""
        return self._proxy("list_executions", {"limit": limit})

    def n8n_create_webhook(self, name: str) -> str:
        """Create a webhook."""
        return self._proxy("create_webhook", {"name": name})

    def register_mcp_tools(self) -> list[Callable[..., str]]:
        return [
            self.n8n_list_workflows,
            self.n8n_get_workflow,
            self.n8n_create_workflow,
            self.n8n_execute_workflow,
            self.n8n_list_executions,
            self.n8n_create_webhook
        ]
