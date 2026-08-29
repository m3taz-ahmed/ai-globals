#!/usr/bin/env python3
"""MetaAdsPlugin for aiZee — proxies to external MCP server.

External MCP server: npx -y @meta/ads-mcp
Required env vars: META_ACCESS_TOKEN, META_AD_ACCOUNT_ID
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from runtime.mcp_client import McpClient
from runtime.plugin import AIOSPlugin


class MetaAdsPlugin(AIOSPlugin):
    """Bridge AIOS kernel to the external meta-ads MCP server."""

    name = "meta-ads"
    version = "0.1.0"

    def on_load(self) -> None:
        """Validate required env vars on plugin load."""
        import os
        missing = [v for v in ("META_ACCESS_TOKEN", "META_AD_ACCOUNT_ID") if not os.environ.get(v)]
        if missing:
            import logging
            logging.getLogger(__name__).warning(
                "%s plugin loaded without %s — tool calls will fail until set",
                self.__class__.__name__, ", ".join(missing),
            )

    def _client(self) -> McpClient:
        return McpClient("meta-ads", self.kernel.root)

    def _proxy(self, tool: str, arguments: dict[str, Any]) -> str:
        """Call a tool on the external MCP server via stdio."""
        try:
            result = self._client().call_tool(tool, arguments)
            return result if isinstance(result, str) else json.dumps(result, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": "MetaAdsPlugin MCP call failed: " + str(exc)})

    def meta_ads_list_campaigns(self, ad_account_id: str) -> str:
        """List campaigns."""
        return self._proxy("list_campaigns", {"ad_account_id": ad_account_id})

    def meta_ads_create_campaign(self, ad_account_id: str, name: str, objective: str) -> str:
        """Create a campaign."""
        return self._proxy("create_campaign", {"ad_account_id": ad_account_id, "name": name, "objective": objective})

    def meta_ads_get_insights(self, ad_account_id: str, campaign_id: str) -> str:
        """Get campaign insights."""
        return self._proxy("get_insights", {"ad_account_id": ad_account_id, "campaign_id": campaign_id})

    def meta_ads_list_ads(self, ad_account_id: str, campaign_id: str) -> str:
        """List ads."""
        return self._proxy("list_ads", {"ad_account_id": ad_account_id, "campaign_id": campaign_id})

    def meta_ads_create_ad_set(self, ad_account_id: str, campaign_id: str, name: str, budget: str) -> str:
        """Create an ad set."""
        return self._proxy("create_ad_set", {"ad_account_id": ad_account_id, "campaign_id": campaign_id, "name": name, "budget": budget})

    def meta_ads_get_audiences(self, ad_account_id: str) -> str:
        """Get audiences."""
        return self._proxy("get_audiences", {"ad_account_id": ad_account_id})

    def register_mcp_tools(self) -> list[Callable[..., str]]:
        return [
            self.meta_ads_list_campaigns,
            self.meta_ads_create_campaign,
            self.meta_ads_get_insights,
            self.meta_ads_list_ads,
            self.meta_ads_create_ad_set,
            self.meta_ads_get_audiences
        ]
