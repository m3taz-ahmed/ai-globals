#!/usr/bin/env python3
"""SendgridPlugin for aiZee — proxies to external MCP server.

External MCP server: npx -y @sendgrid/mcp
Required env vars: SENDGRID_API_KEY
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from runtime.mcp_client import McpClient
from runtime.plugin import AIOSPlugin


class SendgridPlugin(AIOSPlugin):
    """Bridge AIOS kernel to the external sendgrid MCP server."""

    name = "sendgrid"
    version = "0.1.0"

    def on_load(self) -> None:
        """Validate required env vars on plugin load."""
        import os
        missing = [v for v in ("SENDGRID_API_KEY",) if not os.environ.get(v)]
        if missing:
            import logging
            logging.getLogger(__name__).warning(
                "%s plugin loaded without %s — tool calls will fail until set",
                self.__class__.__name__, ", ".join(missing),
            )

    def _client(self) -> McpClient:
        return McpClient("sendgrid", self.kernel.root)

    def _proxy(self, tool: str, arguments: dict[str, Any]) -> str:
        """Call a tool on the external MCP server via stdio."""
        try:
            result = self._client().call_tool(tool, arguments)
            return result if isinstance(result, str) else json.dumps(result, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": "SendgridPlugin MCP call failed: " + str(exc)})

    def sendgrid_list_contacts(self, limit: int = 10) -> str:
        """List contacts."""
        return self._proxy("list_contacts", {"limit": limit})

    def sendgrid_create_contact(self, email: str, first_name: str = "") -> str:
        """Create a contact."""
        return self._proxy("create_contact", {"email": email, "first_name": first_name})

    def sendgrid_send_email(self, to: str, subject: str, html: str) -> str:
        """Send an email."""
        return self._proxy("send_email", {"to": to, "subject": subject, "html": html})

    def sendgrid_list_templates(self) -> str:
        """List templates."""
        return self._proxy("list_templates", {})

    def sendgrid_get_stats(self) -> str:
        """Get send stats."""
        return self._proxy("get_stats", {})

    def sendgrid_create_list(self, name: str) -> str:
        """Create a list."""
        return self._proxy("create_list", {"name": name})

    def register_mcp_tools(self) -> list[Callable[..., str]]:
        return [
            self.sendgrid_list_contacts,
            self.sendgrid_create_contact,
            self.sendgrid_send_email,
            self.sendgrid_list_templates,
            self.sendgrid_get_stats,
            self.sendgrid_create_list
        ]
