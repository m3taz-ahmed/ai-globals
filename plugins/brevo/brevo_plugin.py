#!/usr/bin/env python3
"""BrevoPlugin for aiZee — proxies to external MCP server.

External MCP server: npx -y @brevo/mcp-server
Required env vars: BREVO_API_KEY
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from runtime.mcp_client import McpClient
from runtime.plugin import AIOSPlugin


class BrevoPlugin(AIOSPlugin):
    """Bridge AIOS kernel to the external brevo MCP server."""

    name = "brevo"
    version = "0.1.0"

    def on_load(self) -> None:
        """Validate required env vars on plugin load."""
        import os
        missing = [v for v in ("BREVO_API_KEY",) if not os.environ.get(v)]
        if missing:
            import logging
            logging.getLogger(__name__).warning(
                "%s plugin loaded without %s — tool calls will fail until set",
                self.__class__.__name__, ", ".join(missing),
            )

    def _client(self) -> McpClient:
        return McpClient("brevo", self.kernel.root)

    def _proxy(self, tool: str, arguments: dict[str, Any]) -> str:
        """Call a tool on the external MCP server via stdio."""
        try:
            result = self._client().call_tool(tool, arguments)
            return result if isinstance(result, str) else json.dumps(result, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": "BrevoPlugin MCP call failed: " + str(exc)})

    def brevo_list_contacts(self, limit: int = 10) -> str:
        """List contacts from Brevo (free-first)."""
        return self._proxy("list_contacts", {"limit": limit})

    def brevo_create_contact(self, email: str, attributes: str = "{}") -> str:
        """Create a Brevo contact."""
        return self._proxy("create_contact", {"email": email, "attributes": attributes})

    def brevo_send_email(self, to: str, subject: str, html: str) -> str:
        """Send a transactional email via Brevo."""
        return self._proxy("send_email", {"to": to, "subject": subject, "html": html})

    def brevo_list_campaigns(self, limit: int = 10) -> str:
        """List email campaigns."""
        return self._proxy("list_campaigns", {"limit": limit})

    def brevo_create_campaign(self, name: str, subject: str, html: str) -> str:
        """Create an email campaign."""
        return self._proxy("create_campaign", {"name": name, "subject": subject, "html": html})

    def brevo_get_smtp_stats(self) -> str:
        """Get SMTP send statistics."""
        return self._proxy("get_smtp_stats", {})

    def register_mcp_tools(self) -> list[Callable[..., str]]:
        return [
            self.brevo_list_contacts,
            self.brevo_create_contact,
            self.brevo_send_email,
            self.brevo_list_campaigns,
            self.brevo_create_campaign,
            self.brevo_get_smtp_stats
        ]
