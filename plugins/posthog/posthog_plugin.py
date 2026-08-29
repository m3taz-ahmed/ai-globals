#!/usr/bin/env python3
"""PosthogPlugin for aiZee — proxies to external MCP server.

External MCP server: npx -y @posthog/mcp
Required env vars: POSTHOG_API_KEY, POSTHOG_PROJECT_ID
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from runtime.mcp_client import McpClient
from runtime.plugin import AIOSPlugin


class PosthogPlugin(AIOSPlugin):
    """Bridge AIOS kernel to the external posthog MCP server."""

    name = "posthog"
    version = "0.1.0"

    def on_load(self) -> None:
        """Validate required env vars on plugin load."""
        import os
        missing = [v for v in ("POSTHOG_API_KEY", "POSTHOG_PROJECT_ID") if not os.environ.get(v)]
        if missing:
            import logging
            logging.getLogger(__name__).warning(
                "%s plugin loaded without %s — tool calls will fail until set",
                self.__class__.__name__, ", ".join(missing),
            )

    def _client(self) -> McpClient:
        return McpClient("posthog", self.kernel.root)

    def _proxy(self, tool: str, arguments: dict[str, Any]) -> str:
        """Call a tool on the external MCP server via stdio."""
        try:
            result = self._client().call_tool(tool, arguments)
            return result if isinstance(result, str) else json.dumps(result, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": "PosthogPlugin MCP call failed: " + str(exc)})

    def posthog_list_events(self, limit: int = 10) -> str:
        """List events (free-first)."""
        return self._proxy("list_events", {"limit": limit})

    def posthog_get_insights(self, project_id: str) -> str:
        """Get insights."""
        return self._proxy("get_insights", {"project_id": project_id})

    def posthog_capture_event(self, event: str, distinct_id: str) -> str:
        """Capture an event."""
        return self._proxy("capture_event", {"event": event, "distinct_id": distinct_id})

    def posthog_list_dashboards(self) -> str:
        """List dashboards."""
        return self._proxy("list_dashboards", {})

    def posthog_get_funnels(self, project_id: str) -> str:
        """Get funnels."""
        return self._proxy("get_funnels", {"project_id": project_id})

    def posthog_query(self, sql: str) -> str:
        """Run a SQL query."""
        return self._proxy("query", {"sql": sql})

    def register_mcp_tools(self) -> list[Callable[..., str]]:
        return [
            self.posthog_list_events,
            self.posthog_get_insights,
            self.posthog_capture_event,
            self.posthog_list_dashboards,
            self.posthog_get_funnels,
            self.posthog_query
        ]
