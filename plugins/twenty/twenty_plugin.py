#!/usr/bin/env python3
"""TwentyPlugin for aiZee — proxies to external MCP server.

External MCP server: npx -y @twenty/mcp
Required env vars: TWENTY_API_KEY
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from runtime.mcp_client import McpClient
from runtime.plugin import AIOSPlugin


class TwentyPlugin(AIOSPlugin):
    """Bridge AIOS kernel to the external twenty MCP server."""

    name = "twenty"
    version = "0.1.0"

    def on_load(self) -> None:
        """Validate required env vars on plugin load."""
        import os
        missing = [v for v in ("TWENTY_API_KEY",) if not os.environ.get(v)]
        if missing:
            import logging
            logging.getLogger(__name__).warning(
                "%s plugin loaded without %s — tool calls will fail until set",
                self.__class__.__name__, ", ".join(missing),
            )

    def _client(self) -> McpClient:
        return McpClient("twenty", self.kernel.root)

    def _proxy(self, tool: str, arguments: dict[str, Any]) -> str:
        """Call a tool on the external MCP server via stdio."""
        try:
            result = self._client().call_tool(tool, arguments)
            return result if isinstance(result, str) else json.dumps(result, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": "TwentyPlugin MCP call failed: " + str(exc)})

    def twenty_list_companies(self, limit: int = 10) -> str:
        """List companies (free-first)."""
        return self._proxy("list_companies", {"limit": limit})

    def twenty_get_company(self, company_id: str) -> str:
        """Get a company."""
        return self._proxy("get_company", {"company_id": company_id})

    def twenty_create_person(self, first_name: str, last_name: str, email: str) -> str:
        """Create a person."""
        return self._proxy("create_person", {"first_name": first_name, "last_name": last_name, "email": email})

    def twenty_list_opportunities(self, limit: int = 10) -> str:
        """List opportunities."""
        return self._proxy("list_opportunities", {"limit": limit})

    def twenty_create_task(self, title: str, assignee_id: str) -> str:
        """Create a task."""
        return self._proxy("create_task", {"title": title, "assignee_id": assignee_id})

    def twenty_search(self, query: str) -> str:
        """Search records."""
        return self._proxy("search", {"query": query})

    def register_mcp_tools(self) -> list[Callable[..., str]]:
        return [
            self.twenty_list_companies,
            self.twenty_get_company,
            self.twenty_create_person,
            self.twenty_list_opportunities,
            self.twenty_create_task,
            self.twenty_search
        ]
