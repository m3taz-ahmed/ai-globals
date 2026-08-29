#!/usr/bin/env python3
"""OpenreplayPlugin for aiZee — proxies to external MCP server.

External MCP server: npx -y @openreplay/mcp
Required env vars: OPENREPLAY_API_KEY
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from runtime.mcp_client import McpClient
from runtime.plugin import AIOSPlugin


class OpenreplayPlugin(AIOSPlugin):
    """Bridge AIOS kernel to the external openreplay MCP server."""

    name = "openreplay"
    version = "0.1.0"

    def on_load(self) -> None:
        """Validate required env vars on plugin load."""
        import os
        missing = [v for v in ("OPENREPLAY_API_KEY",) if not os.environ.get(v)]
        if missing:
            import logging
            logging.getLogger(__name__).warning(
                "%s plugin loaded without %s — tool calls will fail until set",
                self.__class__.__name__, ", ".join(missing),
            )

    def _client(self) -> McpClient:
        return McpClient("openreplay", self.kernel.root)

    def _proxy(self, tool: str, arguments: dict[str, Any]) -> str:
        """Call a tool on the external MCP server via stdio."""
        try:
            result = self._client().call_tool(tool, arguments)
            return result if isinstance(result, str) else json.dumps(result, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": "OpenreplayPlugin MCP call failed: " + str(exc)})

    def openreplay_list_sessions(self, limit: int = 10) -> str:
        """List sessions."""
        return self._proxy("list_sessions", {"limit": limit})

    def openreplay_get_session(self, session_id: str) -> str:
        """Get a session."""
        return self._proxy("get_session", {"session_id": session_id})

    def openreplay_get_errors(self, limit: int = 10) -> str:
        """Get errors."""
        return self._proxy("get_errors", {"limit": limit})

    def openreplay_get_metrics(self, session_id: str) -> str:
        """Get metrics."""
        return self._proxy("get_metrics", {"session_id": session_id})

    def openreplay_list_projects(self) -> str:
        """List projects."""
        return self._proxy("list_projects", {})

    def openreplay_get_funnels(self) -> str:
        """Get funnels."""
        return self._proxy("get_funnels", {})

    def register_mcp_tools(self) -> list[Callable[..., str]]:
        return [
            self.openreplay_list_sessions,
            self.openreplay_get_session,
            self.openreplay_get_errors,
            self.openreplay_get_metrics,
            self.openreplay_list_projects,
            self.openreplay_get_funnels
        ]
