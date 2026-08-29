#!/usr/bin/env python3
"""PostizPlugin for aiZee — proxies to external MCP server.

External MCP server: npx -y @postiz/mcp
Required env vars: POSTIZ_API_KEY
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from runtime.mcp_client import McpClient
from runtime.plugin import AIOSPlugin


class PostizPlugin(AIOSPlugin):
    """Bridge AIOS kernel to the external postiz MCP server."""

    name = "postiz"
    version = "0.1.0"

    def on_load(self) -> None:
        """Validate required env vars on plugin load."""
        import os
        missing = [v for v in ("POSTIZ_API_KEY",) if not os.environ.get(v)]
        if missing:
            import logging
            logging.getLogger(__name__).warning(
                "%s plugin loaded without %s — tool calls will fail until set",
                self.__class__.__name__, ", ".join(missing),
            )

    def _client(self) -> McpClient:
        return McpClient("postiz", self.kernel.root)

    def _proxy(self, tool: str, arguments: dict[str, Any]) -> str:
        """Call a tool on the external MCP server via stdio."""
        try:
            result = self._client().call_tool(tool, arguments)
            return result if isinstance(result, str) else json.dumps(result, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": "PostizPlugin MCP call failed: " + str(exc)})

    def postiz_list_posts(self) -> str:
        """List scheduled posts (free-first)."""
        return self._proxy("list_posts", {})

    def postiz_create_post(self, text: str, channels: str) -> str:
        """Create a post."""
        return self._proxy("create_post", {"text": text, "channels": channels})

    def postiz_list_channels(self) -> str:
        """List connected channels."""
        return self._proxy("list_channels", {})

    def postiz_get_analytics(self, post_id: str) -> str:
        """Get post analytics."""
        return self._proxy("get_analytics", {"post_id": post_id})

    def postiz_schedule_post(self, text: str, channels: str, scheduled_at: str) -> str:
        """Schedule a post."""
        return self._proxy("schedule_post", {"text": text, "channels": channels, "scheduled_at": scheduled_at})

    def postiz_list_providers(self) -> str:
        """List providers."""
        return self._proxy("list_providers", {})

    def register_mcp_tools(self) -> list[Callable[..., str]]:
        return [
            self.postiz_list_posts,
            self.postiz_create_post,
            self.postiz_list_channels,
            self.postiz_get_analytics,
            self.postiz_schedule_post,
            self.postiz_list_providers
        ]
