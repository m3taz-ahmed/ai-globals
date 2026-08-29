#!/usr/bin/env python3
"""ErpnextPlugin for aiZee — proxies to external MCP server.

External MCP server: npx -y @erpnext/mcp
Required env vars: ERPNEXT_API_KEY, ERPNEXT_URL
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from runtime.mcp_client import McpClient
from runtime.plugin import AIOSPlugin


class ErpnextPlugin(AIOSPlugin):
    """Bridge AIOS kernel to the external erpnext MCP server."""

    name = "erpnext"
    version = "0.1.0"

    def on_load(self) -> None:
        """Validate required env vars on plugin load."""
        import os
        missing = [v for v in ("ERPNEXT_API_KEY", "ERPNEXT_URL") if not os.environ.get(v)]
        if missing:
            import logging
            logging.getLogger(__name__).warning(
                "%s plugin loaded without %s — tool calls will fail until set",
                self.__class__.__name__, ", ".join(missing),
            )

    def _client(self) -> McpClient:
        return McpClient("erpnext", self.kernel.root)

    def _proxy(self, tool: str, arguments: dict[str, Any]) -> str:
        """Call a tool on the external MCP server via stdio."""
        try:
            result = self._client().call_tool(tool, arguments)
            return result if isinstance(result, str) else json.dumps(result, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": "ErpnextPlugin MCP call failed: " + str(exc)})

    def erpnext_list_customers(self, limit: int = 10) -> str:
        """List customers."""
        return self._proxy("list_customers", {"limit": limit})

    def erpnext_get_customer(self, customer_id: str) -> str:
        """Get a customer."""
        return self._proxy("get_customer", {"customer_id": customer_id})

    def erpnext_list_invoices(self, limit: int = 10) -> str:
        """List invoices."""
        return self._proxy("list_invoices", {"limit": limit})

    def erpnext_create_invoice(self, customer_id: str, items: str) -> str:
        """Create an invoice."""
        return self._proxy("create_invoice", {"customer_id": customer_id, "items": items})

    def erpnext_list_items(self, limit: int = 10) -> str:
        """List items."""
        return self._proxy("list_items", {"limit": limit})

    def erpnext_get_stock_balance(self) -> str:
        """Get stock balance."""
        return self._proxy("get_stock_balance", {})

    def register_mcp_tools(self) -> list[Callable[..., str]]:
        return [
            self.erpnext_list_customers,
            self.erpnext_get_customer,
            self.erpnext_list_invoices,
            self.erpnext_create_invoice,
            self.erpnext_list_items,
            self.erpnext_get_stock_balance
        ]
