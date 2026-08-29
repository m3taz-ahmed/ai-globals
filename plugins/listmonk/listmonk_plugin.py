#!/usr/bin/env python3
"""ListmonkPlugin for aiZee — proxies to external MCP server.

External MCP server: npx -y listmonk-mcp
Required env vars: LISTMONK_API_URL, LISTMONK_API_KEY
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from runtime.mcp_client import McpClient
from runtime.plugin import AIOSPlugin


class ListmonkPlugin(AIOSPlugin):
    """Bridge AIOS kernel to the external listmonk MCP server."""

    name = "listmonk"
    version = "0.1.0"

    def on_load(self) -> None:
        """Validate required env vars on plugin load."""
        import os
        missing = [v for v in ("LISTMONK_API_URL", "LISTMONK_API_KEY") if not os.environ.get(v)]
        if missing:
            import logging
            logging.getLogger(__name__).warning(
                "%s plugin loaded without %s — tool calls will fail until set",
                self.__class__.__name__, ", ".join(missing),
            )

    def _client(self) -> McpClient:
        return McpClient("listmonk", self.kernel.root)

    def _proxy(self, tool: str, arguments: dict[str, Any]) -> str:
        """Call a tool on the external MCP server via stdio."""
        try:
            result = self._client().call_tool(tool, arguments)
            return result if isinstance(result, str) else json.dumps(result, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": "ListmonkPlugin MCP call failed: " + str(exc)})

    def listmonk_list_subscribers(self, limit: int = 10) -> str:
        """List subscribers (self-hosted, free-first)."""
        return self._proxy("list_subscribers", {"limit": limit})

    def listmonk_create_subscriber(self, email: str, name: str = "") -> str:
        """Add a subscriber."""
        return self._proxy("create_subscriber", {"email": email, "name": name})

    def listmonk_list_campaigns(self) -> str:
        """List campaigns."""
        return self._proxy("list_campaigns", {})

    def listmonk_create_campaign(self, name: str, subject: str, body: str) -> str:
        """Create a campaign."""
        return self._proxy("create_campaign", {"name": name, "subject": subject, "body": body})

    def listmonk_send_transactional(self, to: str, subject: str, body: str) -> str:
        """Send a transactional email."""
        return self._proxy("send_transactional", {"to": to, "subject": subject, "body": body})

    def listmonk_list_lists(self) -> str:
        """List subscriber lists."""
        return self._proxy("list_lists", {})

    def register_mcp_tools(self) -> list[Callable[..., str]]:
        return [
            self.listmonk_list_subscribers,
            self.listmonk_create_subscriber,
            self.listmonk_list_campaigns,
            self.listmonk_create_campaign,
            self.listmonk_send_transactional,
            self.listmonk_list_lists
        ]
