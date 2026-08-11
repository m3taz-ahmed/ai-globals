#!/usr/bin/env python3
"""Upwork plugin for AI Global OS — proxies to @furkankoykiran/upwork-mcp.

Requires UPWORK_CLIENT_ID and UPWORK_CLIENT_SECRET env vars and an authenticated
session (run `npx @furkankoykiran/upwork-mcp auth` first).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from runtime.mcp_client import McpClient
from runtime.plugin import AIOSPlugin


class UpworkPlugin(AIOSPlugin):
    """Bridge AIOS kernel to the external Upwork MCP server."""

    name = "upwork"
    version = "0.1.0"

    def on_load(self) -> None:
        """Validate that credentials are present; warn (do not crash) if missing."""
        import os
        import warnings

        missing = [v for v in ("UPWORK_CLIENT_ID", "UPWORK_CLIENT_SECRET") if not os.environ.get(v)]
        if missing:
            warnings.warn(
                f"Upwork plugin enabled but {', '.join(missing)} env var(s) missing; "
                "tool calls will fail until credentials are set.",
                stacklevel=2,
            )

    def _client(self) -> McpClient:
        return McpClient("upwork", self.kernel.root)

    def upwork_search_jobs(self, query: str, limit: int = 10) -> str:
        """Search Upwork jobs by keyword."""
        return self._proxy("search_jobs", {"query": query, "limit": limit})

    def upwork_get_job_details(self, job_id: str) -> str:
        """Get details for a specific Upwork job."""
        return self._proxy("get_job_details", {"job_id": job_id})

    def upwork_get_profile(self) -> str:
        """Get the authenticated freelancer's profile."""
        return self._proxy("get_profile", {})

    def upwork_list_contracts(self, status: str = "active") -> str:
        """List contracts filtered by status."""
        return self._proxy("list_contracts", {"status": status})

    def upwork_get_balance(self) -> str:
        """Get account balance."""
        return self._proxy("get_balance", {})

    def upwork_list_saved_jobs(self) -> str:
        """List saved/bookmarked jobs."""
        return self._proxy("list_saved_jobs", {})

    def upwork_save_job(self, job_id: str) -> str:
        """Save a job to bookmarks."""
        return self._proxy("save_job", {"job_id": job_id})

    def upwork_get_proposal_stats(self) -> str:
        """Get proposal statistics."""
        return self._proxy("get_proposal_stats", {})

    def _proxy(self, tool: str, arguments: dict[str, Any]) -> str:
        """Call a tool on the external Upwork MCP server via stdio."""
        try:
            result = self._client().call_tool(tool, arguments)
            return result if isinstance(result, str) else json.dumps(result, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": f"Upwork MCP call failed: {exc!s}"})

    def register_mcp_tools(self) -> list[Callable[..., str]]:
        return [
            self.upwork_search_jobs,
            self.upwork_get_job_details,
            self.upwork_get_profile,
            self.upwork_list_contracts,
            self.upwork_get_balance,
            self.upwork_list_saved_jobs,
            self.upwork_save_job,
            self.upwork_get_proposal_stats,
        ]
