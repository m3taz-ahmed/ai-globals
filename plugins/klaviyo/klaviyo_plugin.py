#!/usr/bin/env python3
"""KlaviyoPlugin for aiZee — proxies to external MCP server.

External MCP server: npx -y @klaviyo/mcp
Required env vars: KLAVIYO_API_KEY
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from runtime.mcp_client import McpClient
from runtime.plugin import AIOSPlugin


class KlaviyoPlugin(AIOSPlugin):
    """Bridge AIOS kernel to the external klaviyo MCP server."""

    name = "klaviyo"
    version = "0.1.0"

    def on_load(self) -> None:
        """Validate required env vars on plugin load."""
        import os
        missing = [v for v in ("KLAVIYO_API_KEY",) if not os.environ.get(v)]
        if missing:
            import logging
            logging.getLogger(__name__).warning(
                "%s plugin loaded without %s — tool calls will fail until set",
                self.__class__.__name__, ", ".join(missing),
            )

    def _client(self) -> McpClient:
        return McpClient("klaviyo", self.kernel.root)

    def _proxy(self, tool: str, arguments: dict[str, Any]) -> str:
        """Call a tool on the external MCP server via stdio."""
        try:
            result = self._client().call_tool(tool, arguments)
            return result if isinstance(result, str) else json.dumps(result, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": "KlaviyoPlugin MCP call failed: " + str(exc)})

    def klaviyo_list_profiles(self, limit: int = 10) -> str:
        """List profiles."""
        return self._proxy("list_profiles", {"limit": limit})

    def klaviyo_get_profile(self, profile_id: str) -> str:
        """Get a profile."""
        return self._proxy("get_profile", {"profile_id": profile_id})

    def klaviyo_create_campaign(self, name: str, list_id: str) -> str:
        """Create a campaign."""
        return self._proxy("create_campaign", {"name": name, "list_id": list_id})

    def klaviyo_send_email(self, list_id: str, subject: str, html: str) -> str:
        """Send an email."""
        return self._proxy("send_email", {"list_id": list_id, "subject": subject, "html": html})

    def klaviyo_get_metrics(self, limit: int = 10) -> str:
        """Get metrics."""
        return self._proxy("get_metrics", {"limit": limit})

    def klaviyo_list_flows(self) -> str:
        """List flows."""
        return self._proxy("list_flows", {})

    def register_mcp_tools(self) -> list[Callable[..., str]]:
        return [
            self.klaviyo_list_profiles,
            self.klaviyo_get_profile,
            self.klaviyo_create_campaign,
            self.klaviyo_send_email,
            self.klaviyo_get_metrics,
            self.klaviyo_list_flows
        ]
