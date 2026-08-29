#!/usr/bin/env python3
"""TiktokAdsPlugin for aiZee — proxies to external MCP server.

External MCP server: npx -y @tiktok/ads-mcp
Required env vars: TIKTOK_ACCESS_TOKEN, TIKTOK_ADVERTISER_ID
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from runtime.mcp_client import McpClient
from runtime.plugin import AIOSPlugin


class TiktokAdsPlugin(AIOSPlugin):
    """Bridge AIOS kernel to the external tiktok-ads MCP server."""

    name = "tiktok-ads"
    version = "0.1.0"

    def on_load(self) -> None:
        """Validate required env vars on plugin load."""
        import os
        missing = [v for v in ("TIKTOK_ACCESS_TOKEN", "TIKTOK_ADVERTISER_ID") if not os.environ.get(v)]
        if missing:
            import logging
            logging.getLogger(__name__).warning(
                "%s plugin loaded without %s — tool calls will fail until set",
                self.__class__.__name__, ", ".join(missing),
            )

    def _client(self) -> McpClient:
        return McpClient("tiktok-ads", self.kernel.root)

    def _proxy(self, tool: str, arguments: dict[str, Any]) -> str:
        """Call a tool on the external MCP server via stdio."""
        try:
            result = self._client().call_tool(tool, arguments)
            return result if isinstance(result, str) else json.dumps(result, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": "TiktokAdsPlugin MCP call failed: " + str(exc)})

    def tiktok_ads_list_campaigns(self, advertiser_id: str) -> str:
        """List campaigns."""
        return self._proxy("list_campaigns", {"advertiser_id": advertiser_id})

    def tiktok_ads_create_campaign(self, advertiser_id: str, name: str, objective: str) -> str:
        """Create a campaign."""
        return self._proxy("create_campaign", {"advertiser_id": advertiser_id, "name": name, "objective": objective})

    def tiktok_ads_get_insights(self, advertiser_id: str, campaign_id: str) -> str:
        """Get insights."""
        return self._proxy("get_insights", {"advertiser_id": advertiser_id, "campaign_id": campaign_id})

    def tiktok_ads_list_ads(self, advertiser_id: str, campaign_id: str) -> str:
        """List ads."""
        return self._proxy("list_ads", {"advertiser_id": advertiser_id, "campaign_id": campaign_id})

    def tiktok_ads_create_ad(self, advertiser_id: str, ad_group_id: str, name: str) -> str:
        """Create an ad."""
        return self._proxy("create_ad", {"advertiser_id": advertiser_id, "ad_group_id": ad_group_id, "name": name})

    def tiktok_ads_get_audiences(self, advertiser_id: str) -> str:
        """Get audiences."""
        return self._proxy("get_audiences", {"advertiser_id": advertiser_id})

    def register_mcp_tools(self) -> list[Callable[..., str]]:
        return [
            self.tiktok_ads_list_campaigns,
            self.tiktok_ads_create_campaign,
            self.tiktok_ads_get_insights,
            self.tiktok_ads_list_ads,
            self.tiktok_ads_create_ad,
            self.tiktok_ads_get_audiences
        ]
