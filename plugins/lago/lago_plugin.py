#!/usr/bin/env python3
"""LagoPlugin for aiZee — proxies to external MCP server.

External MCP server: npx -y @getlago/mcp
Required env vars: LAGO_API_KEY, LAGO_API_URL
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from runtime.mcp_client import McpClient
from runtime.plugin import AIOSPlugin


class LagoPlugin(AIOSPlugin):
    """Bridge AIOS kernel to the external lago MCP server."""

    name = "lago"
    version = "0.1.0"

    def on_load(self) -> None:
        """Validate required env vars on plugin load."""
        import os
        missing = [v for v in ("LAGO_API_KEY", "LAGO_API_URL") if not os.environ.get(v)]
        if missing:
            import logging
            logging.getLogger(__name__).warning(
                "%s plugin loaded without %s — tool calls will fail until set",
                self.__class__.__name__, ", ".join(missing),
            )

    def _client(self) -> McpClient:
        return McpClient("lago", self.kernel.root)

    def _proxy(self, tool: str, arguments: dict[str, Any]) -> str:
        """Call a tool on the external MCP server via stdio."""
        try:
            result = self._client().call_tool(tool, arguments)
            return result if isinstance(result, str) else json.dumps(result, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": "LagoPlugin MCP call failed: " + str(exc)})

    def lago_list_customers(self, limit: int = 10) -> str:
        """List customers."""
        return self._proxy("list_customers", {"limit": limit})

    def lago_get_customer(self, customer_id: str) -> str:
        """Get a customer."""
        return self._proxy("get_customer", {"customer_id": customer_id})

    def lago_create_invoice(self, customer_id: str, amount: str) -> str:
        """Create an invoice."""
        return self._proxy("create_invoice", {"customer_id": customer_id, "amount": amount})

    def lago_list_subscriptions(self, limit: int = 10) -> str:
        """List subscriptions."""
        return self._proxy("list_subscriptions", {"limit": limit})

    def lago_get_usage(self, customer_id: str) -> str:
        """Get usage."""
        return self._proxy("get_usage", {"customer_id": customer_id})

    def lago_list_events(self, limit: int = 10) -> str:
        """List events."""
        return self._proxy("list_events", {"limit": limit})

    def register_mcp_tools(self) -> list[Callable[..., str]]:
        return [
            self.lago_list_customers,
            self.lago_get_customer,
            self.lago_create_invoice,
            self.lago_list_subscriptions,
            self.lago_get_usage,
            self.lago_list_events
        ]
