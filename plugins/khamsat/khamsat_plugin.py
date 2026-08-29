#!/usr/bin/env python3
"""KhamsatPlugin for aiZee — proxies to external MCP server.

External MCP server: npx -y @khamsat/mcp
Required env vars: KHAMSAT_API_TOKEN

NOTE: Arabic freelance marketplace (Egypt/Arab world). RTL content; offers accept Arabic. Currency EGP.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from runtime.mcp_client import McpClient
from runtime.plugin import AIOSPlugin


class KhamsatPlugin(AIOSPlugin):
    """Bridge AIOS kernel to the external khamsat MCP server."""

    name = "khamsat"
    version = "0.1.0"

    def on_load(self) -> None:
        """Validate required env vars on plugin load."""
        import os
        missing = [v for v in ("KHAMSAT_API_TOKEN",) if not os.environ.get(v)]
        if missing:
            import logging
            logging.getLogger(__name__).warning(
                "%s plugin loaded without %s — tool calls will fail until set",
                self.__class__.__name__, ", ".join(missing),
            )

    def _client(self) -> McpClient:
        return McpClient("khamsat", self.kernel.root)

    def _proxy(self, tool: str, arguments: dict[str, Any]) -> str:
        """Call a tool on the external MCP server via stdio."""
        try:
            result = self._client().call_tool(tool, arguments)
            return result if isinstance(result, str) else json.dumps(result, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": "KhamsatPlugin MCP call failed: " + str(exc)})

    def khamsat_search_services(self, query: str, limit: int = 10) -> str:
        """Search services (Arabic-first; RTL)."""
        return self._proxy("search_services", {"query": query, "limit": limit})

    def khamsat_get_service(self, service_id: str) -> str:
        """Get service details."""
        return self._proxy("get_service", {"service_id": service_id})

    def khamsat_list_orders(self, status: str = "active") -> str:
        """List orders by status."""
        return self._proxy("list_orders", {"status": status})

    def khamsat_create_offer(self, title: str, price: str, description: str) -> str:
        """Create an offer (Arabic supported)."""
        return self._proxy("create_offer", {"title": title, "price": price, "description": description})

    def khamsat_get_profile(self) -> str:
        """Get profile."""
        return self._proxy("get_profile", {})

    def khamsat_list_requests(self, limit: int = 10) -> str:
        """List buyer requests."""
        return self._proxy("list_requests", {"limit": limit})

    def register_mcp_tools(self) -> list[Callable[..., str]]:
        return [
            self.khamsat_search_services,
            self.khamsat_get_service,
            self.khamsat_list_orders,
            self.khamsat_create_offer,
            self.khamsat_get_profile,
            self.khamsat_list_requests
        ]
