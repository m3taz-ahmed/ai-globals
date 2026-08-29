#!/usr/bin/env python3
"""MostaqlPlugin for aiZee — proxies to external MCP server.

External MCP server: npx -y @mostaql/mcp
Required env vars: MOSTAQL_API_TOKEN

NOTE: Arabic freelance marketplace (Saudi/UAE). Returns RTL-aware content; proposals accept Arabic text. Currency AED/SAR.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from runtime.mcp_client import McpClient
from runtime.plugin import AIOSPlugin


class MostaqlPlugin(AIOSPlugin):
    """Bridge AIOS kernel to the external mostaql MCP server."""

    name = "mostaql"
    version = "0.1.0"

    def on_load(self) -> None:
        """Validate required env vars on plugin load."""
        import os
        missing = [v for v in ("MOSTAQL_API_TOKEN",) if not os.environ.get(v)]
        if missing:
            import logging
            logging.getLogger(__name__).warning(
                "%s plugin loaded without %s — tool calls will fail until set",
                self.__class__.__name__, ", ".join(missing),
            )

    def _client(self) -> McpClient:
        return McpClient("mostaql", self.kernel.root)

    def _proxy(self, tool: str, arguments: dict[str, Any]) -> str:
        """Call a tool on the external MCP server via stdio."""
        try:
            result = self._client().call_tool(tool, arguments)
            return result if isinstance(result, str) else json.dumps(result, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": "MostaqlPlugin MCP call failed: " + str(exc)})

    def mostaql_search_projects(self, query: str, limit: int = 10) -> str:
        """Search projects (Arabic-first; RTL content)."""
        return self._proxy("search_projects", {"query": query, "limit": limit})

    def mostaql_get_project(self, project_id: str) -> str:
        """Get project details."""
        return self._proxy("get_project", {"project_id": project_id})

    def mostaql_list_bids(self, limit: int = 10) -> str:
        """List your bids."""
        return self._proxy("list_bids", {"limit": limit})

    def mostaql_create_bid(self, project_id: str, amount: str, proposal: str) -> str:
        """Place a bid (Arabic proposal supported)."""
        return self._proxy("create_bid", {"project_id": project_id, "amount": amount, "proposal": proposal})

    def mostaql_get_profile(self) -> str:
        """Get freelancer profile."""
        return self._proxy("get_profile", {})

    def mostaql_list_skills(self) -> str:
        """List skills/categories."""
        return self._proxy("list_skills", {})

    def register_mcp_tools(self) -> list[Callable[..., str]]:
        return [
            self.mostaql_search_projects,
            self.mostaql_get_project,
            self.mostaql_list_bids,
            self.mostaql_create_bid,
            self.mostaql_get_profile,
            self.mostaql_list_skills
        ]
