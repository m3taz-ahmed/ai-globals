#!/usr/bin/env python3
"""HubspotPlugin for aiZee — proxies to external MCP server.

External MCP server: npx -y @hubspot/mcp
Required env vars: HUBSPOT_API_KEY
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from runtime.mcp_client import McpClient
from runtime.plugin import AIOSPlugin


class HubspotPlugin(AIOSPlugin):
    """Bridge AIOS kernel to the external hubspot MCP server."""

    name = "hubspot"
    version = "0.1.0"

    def on_load(self) -> None:
        """Validate required env vars on plugin load."""
        import os
        missing = [v for v in ("HUBSPOT_API_KEY",) if not os.environ.get(v)]
        if missing:
            import logging
            logging.getLogger(__name__).warning(
                "%s plugin loaded without %s — tool calls will fail until set",
                self.__class__.__name__, ", ".join(missing),
            )

    def _client(self) -> McpClient:
        return McpClient("hubspot", self.kernel.root)

    def _proxy(self, tool: str, arguments: dict[str, Any]) -> str:
        """Call a tool on the external MCP server via stdio."""
        try:
            result = self._client().call_tool(tool, arguments)
            return result if isinstance(result, str) else json.dumps(result, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": "HubspotPlugin MCP call failed: " + str(exc)})

    def hubspot_list_contacts(self, limit: int = 10) -> str:
        """List contacts."""
        return self._proxy("list_contacts", {"limit": limit})

    def hubspot_create_contact(self, email: str, first_name: str = "") -> str:
        """Create a contact."""
        return self._proxy("create_contact", {"email": email, "first_name": first_name})

    def hubspot_list_deals(self, limit: int = 10) -> str:
        """List deals."""
        return self._proxy("list_deals", {"limit": limit})

    def hubspot_create_deal(self, name: str, amount: str) -> str:
        """Create a deal."""
        return self._proxy("create_deal", {"name": name, "amount": amount})

    def hubspot_get_contact(self, contact_id: str) -> str:
        """Get a contact."""
        return self._proxy("get_contact", {"contact_id": contact_id})

    def hubspot_list_companies(self, limit: int = 10) -> str:
        """List companies."""
        return self._proxy("list_companies", {"limit": limit})

    def register_mcp_tools(self) -> list[Callable[..., str]]:
        return [
            self.hubspot_list_contacts,
            self.hubspot_create_contact,
            self.hubspot_list_deals,
            self.hubspot_create_deal,
            self.hubspot_get_contact,
            self.hubspot_list_companies
        ]
