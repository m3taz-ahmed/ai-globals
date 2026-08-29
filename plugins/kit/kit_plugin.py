#!/usr/bin/env python3
"""KitPlugin for aiZee — proxies to external MCP server.

External MCP server: npx -y @kit/mcp
Required env vars: KIT_API_KEY
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from runtime.mcp_client import McpClient
from runtime.plugin import AIOSPlugin


class KitPlugin(AIOSPlugin):
    """Bridge AIOS kernel to the external kit MCP server."""

    name = "kit"
    version = "0.1.0"

    def on_load(self) -> None:
        """Validate required env vars on plugin load."""
        import os
        missing = [v for v in ("KIT_API_KEY",) if not os.environ.get(v)]
        if missing:
            import logging
            logging.getLogger(__name__).warning(
                "%s plugin loaded without %s — tool calls will fail until set",
                self.__class__.__name__, ", ".join(missing),
            )

    def _client(self) -> McpClient:
        return McpClient("kit", self.kernel.root)

    def _proxy(self, tool: str, arguments: dict[str, Any]) -> str:
        """Call a tool on the external MCP server via stdio."""
        try:
            result = self._client().call_tool(tool, arguments)
            return result if isinstance(result, str) else json.dumps(result, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": "KitPlugin MCP call failed: " + str(exc)})

    def kit_list_subscribers(self, limit: int = 10) -> str:
        """List subscribers."""
        return self._proxy("list_subscribers", {"limit": limit})

    def kit_add_subscriber(self, email: str, first_name: str = "") -> str:
        """Add a subscriber."""
        return self._proxy("add_subscriber", {"email": email, "first_name": first_name})

    def kit_list_sequences(self) -> str:
        """List sequences."""
        return self._proxy("list_sequences", {})

    def kit_create_broadcast(self, subject: str, content: str) -> str:
        """Create a broadcast."""
        return self._proxy("create_broadcast", {"subject": subject, "content": content})

    def kit_get_tags(self) -> str:
        """Get tags."""
        return self._proxy("get_tags", {})

    def kit_add_tag(self, subscriber_id: str, tag_id: str) -> str:
        """Add a tag to a subscriber."""
        return self._proxy("add_tag", {"subscriber_id": subscriber_id, "tag_id": tag_id})

    def register_mcp_tools(self) -> list[Callable[..., str]]:
        return [
            self.kit_list_subscribers,
            self.kit_add_subscriber,
            self.kit_list_sequences,
            self.kit_create_broadcast,
            self.kit_get_tags,
            self.kit_add_tag
        ]
