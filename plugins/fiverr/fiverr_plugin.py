#!/usr/bin/env python3
"""Fiverr plugin for aiZee — proxies to KyuRish/fiverr-mcp-server.

No API key required (scraper-based). READ-ONLY: search gigs, get details, view
sellers and reviews. Bidding/messaging are NOT exposed because they violate
Fiverr ToS.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from runtime.mcp_client import McpClient
from runtime.plugin import AIOSPlugin


class FiverrPlugin(AIOSPlugin):
    """Bridge AIOS kernel to the external Fiverr MCP server (search-only)."""

    name = "fiverr"
    version = "0.1.0"

    def on_load(self) -> None:
        """No credentials required for Fiverr search."""
        return None

    def _client(self) -> McpClient:
        return McpClient("fiverr", self.kernel.root)

    def fiverr_search_gigs(
        self,
        query: str,
        min_price: float | None = None,
        max_price: float | None = None,
        seller_level: str | None = None,
        sort_by: str = "relevance",
        page: int = 1,
    ) -> str:
        """Search Fiverr gigs by keyword with optional filters."""
        args: dict[str, Any] = {"query": query, "sort_by": sort_by, "page": page}
        if min_price is not None:
            args["min_price"] = min_price
        if max_price is not None:
            args["max_price"] = max_price
        if seller_level is not None:
            args["seller_level"] = seller_level
        return self._proxy("search_gigs", args)

    def fiverr_get_gig_details(self, gig_id: str) -> str:
        """Get full details for a specific gig including pricing tiers."""
        return self._proxy("get_gig_details", {"gig_id": gig_id})

    def fiverr_get_seller_profile(self, seller_username: str) -> str:
        """View a seller's profile with certifications, languages, and gigs."""
        return self._proxy("get_seller_profile", {"seller_username": seller_username})

    def fiverr_get_gig_reviews(self, gig_id: str) -> str:
        """Read reviews for a specific gig."""
        return self._proxy("get_gig_reviews", {"gig_id": gig_id})

    def fiverr_list_categories(self) -> str:
        """List valid Fiverr category slugs for filtered search."""
        return self._proxy("list_categories", {})

    def _proxy(self, tool: str, arguments: dict[str, Any]) -> str:
        """Call a tool on the external Fiverr MCP server via stdio."""
        try:
            result = self._client().call_tool(tool, arguments)
            return result if isinstance(result, str) else json.dumps(result, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": f"Fiverr MCP call failed: {exc!s}"})

    def register_mcp_tools(self) -> list[Callable[..., str]]:
        return [
            self.fiverr_search_gigs,
            self.fiverr_get_gig_details,
            self.fiverr_get_seller_profile,
            self.fiverr_get_gig_reviews,
            self.fiverr_list_categories,
        ]
