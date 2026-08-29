#!/usr/bin/env python3
"""GoogleAdsPlugin for aiZee — proxies to external MCP server.

External MCP server: npx -y @google-ads/mcp
Required env vars: GOOGLE_ADS_DEVELOPER_TOKEN, GOOGLE_ADS_CLIENT_ID, GOOGLE_ADS_CLIENT_SECRET
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from runtime.mcp_client import McpClient
from runtime.plugin import AIOSPlugin


class GoogleAdsPlugin(AIOSPlugin):
    """Bridge AIOS kernel to the external google-ads MCP server."""

    name = "google-ads"
    version = "0.1.0"

    def on_load(self) -> None:
        """Validate required env vars on plugin load."""
        import os
        missing = [v for v in ("GOOGLE_ADS_DEVELOPER_TOKEN", "GOOGLE_ADS_CLIENT_ID", "GOOGLE_ADS_CLIENT_SECRET") if not os.environ.get(v)]
        if missing:
            import logging
            logging.getLogger(__name__).warning(
                "%s plugin loaded without %s — tool calls will fail until set",
                self.__class__.__name__, ", ".join(missing),
            )

    def _client(self) -> McpClient:
        return McpClient("google-ads", self.kernel.root)

    def _proxy(self, tool: str, arguments: dict[str, Any]) -> str:
        """Call a tool on the external MCP server via stdio."""
        try:
            result = self._client().call_tool(tool, arguments)
            return result if isinstance(result, str) else json.dumps(result, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": "GoogleAdsPlugin MCP call failed: " + str(exc)})

    def google_ads_list_campaigns(self, customer_id: str) -> str:
        """List campaigns."""
        return self._proxy("list_campaigns", {"customer_id": customer_id})

    def google_ads_create_campaign(self, customer_id: str, name: str, budget: str) -> str:
        """Create a campaign."""
        return self._proxy("create_campaign", {"customer_id": customer_id, "name": name, "budget": budget})

    def google_ads_get_metrics(self, customer_id: str, campaign_id: str) -> str:
        """Get campaign metrics."""
        return self._proxy("get_campaign_metrics", {"customer_id": customer_id, "campaign_id": campaign_id})

    def google_ads_list_ad_groups(self, customer_id: str, campaign_id: str) -> str:
        """List ad groups."""
        return self._proxy("list_ad_groups", {"customer_id": customer_id, "campaign_id": campaign_id})

    def google_ads_create_ad(self, customer_id: str, ad_group_id: str, headline: str) -> str:
        """Create an ad."""
        return self._proxy("create_ad", {"customer_id": customer_id, "ad_group_id": ad_group_id, "headline": headline})

    def google_ads_get_keyword_ideas(self, customer_id: str, keyword: str) -> str:
        """Get keyword ideas."""
        return self._proxy("get_keyword_ideas", {"customer_id": customer_id, "keyword": keyword})

    def register_mcp_tools(self) -> list[Callable[..., str]]:
        return [
            self.google_ads_list_campaigns,
            self.google_ads_create_campaign,
            self.google_ads_get_metrics,
            self.google_ads_list_ad_groups,
            self.google_ads_create_ad,
            self.google_ads_get_keyword_ideas
        ]
