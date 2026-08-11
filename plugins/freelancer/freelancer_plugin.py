#!/usr/bin/env python3
"""Freelancer.com plugin for AI Global OS — proxies to godesigntech/freelancer-mcp-server.

Requires FREELANCER_OAUTH_TOKEN env var (or FREELANCER_ACCOUNTS JSON for multi-account).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from runtime.mcp_client import McpClient
from runtime.plugin import AIOSPlugin


class FreelancerPlugin(AIOSPlugin):
    """Bridge AIOS kernel to the external Freelancer.com MCP server."""

    name = "freelancer"
    version = "0.1.0"

    def on_load(self) -> None:
        """Validate that credentials are present; warn (do not crash) if missing."""
        import os
        import warnings

        if not os.environ.get("FREELANCER_OAUTH_TOKEN") and not os.environ.get("FREELANCER_ACCOUNTS"):
            warnings.warn(
                "Freelancer plugin enabled but FREELANCER_OAUTH_TOKEN (or FREELANCER_ACCOUNTS) "
                "env var missing; tool calls will fail until credentials are set.",
                stacklevel=2,
            )

    def _client(self) -> McpClient:
        return McpClient("freelancer", self.kernel.root)

    def freelancer_search_projects(self, query: str, limit: int = 10) -> str:
        """Search Freelancer.com projects by keyword."""
        return self._proxy("freelancer_search_projects", {"query": query, "limit": limit})

    def freelancer_get_project(self, project_id: int) -> str:
        """Get details for a specific project."""
        return self._proxy("freelancer_get_project", {"project_id": project_id})

    def freelancer_my_projects(self, status: str = "active") -> str:
        """List the authenticated user's projects."""
        return self._proxy("freelancer_my_projects", {"status": status})

    def freelancer_my_bids(self, status: str = "awarded") -> str:
        """List the user's bids filtered by status."""
        return self._proxy("freelancer_my_bids", {"status": status})

    def freelancer_place_bid(self, project_id: int, amount: float, days: int, description: str) -> str:
        """Place a bid on a project. Requires explicit user approval (policy gate)."""
        return self._proxy(
            "freelancer_place_bid",
            {"project_id": project_id, "amount": amount, "days": days, "description": description},
        )

    def freelancer_get_milestones(self, project_id: int) -> str:
        """Get milestones for a project."""
        return self._proxy("freelancer_get_milestones", {"project_id": project_id})

    def freelancer_list_threads(self) -> str:
        """List inbox threads."""
        return self._proxy("freelancer_list_threads", {})

    def freelancer_get_messages(self, thread_id: int) -> str:
        """Get messages in a thread."""
        return self._proxy("freelancer_get_messages", {"thread_id": thread_id})

    def freelancer_send_message(self, thread_id: int, message: str) -> str:
        """Send a message in a thread. Requires explicit user approval (policy gate)."""
        return self._proxy("freelancer_send_message", {"thread_id": thread_id, "message": message})

    def freelancer_get_self(self) -> str:
        """Get the authenticated user's profile."""
        return self._proxy("freelancer_get_self", {})

    def freelancer_list_accounts(self) -> str:
        """List connected Freelancer accounts (multi-account support)."""
        return self._proxy("freelancer_list_accounts", {})

    def _proxy(self, tool: str, arguments: dict[str, Any]) -> str:
        """Call a tool on the external Freelancer MCP server via stdio."""
        try:
            result = self._client().call_tool(tool, arguments)
            return result if isinstance(result, str) else json.dumps(result, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": f"Freelancer MCP call failed: {exc!s}"})

    def register_mcp_tools(self) -> list[Callable[..., str]]:
        return [
            self.freelancer_search_projects,
            self.freelancer_get_project,
            self.freelancer_my_projects,
            self.freelancer_my_bids,
            self.freelancer_place_bid,
            self.freelancer_get_milestones,
            self.freelancer_list_threads,
            self.freelancer_get_messages,
            self.freelancer_send_message,
            self.freelancer_get_self,
            self.freelancer_list_accounts,
        ]
