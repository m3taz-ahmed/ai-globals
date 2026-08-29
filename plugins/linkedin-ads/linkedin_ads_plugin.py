#!/usr/bin/env python3
"""LinkedinAdsPlugin for aiZee — proxies to external MCP server.

External MCP server: npx -y @linkedin/ads-mcp
Required env vars: LINKEDIN_ACCESS_TOKEN
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from runtime.mcp_client import McpClient
from runtime.plugin import AIOSPlugin


class LinkedinAdsPlugin(AIOSPlugin):
    """Bridge AIOS kernel to the external linkedin-ads MCP server."""

    name = "linkedin-ads"
    version = "0.1.0"

    def on_load(self) -> None:
        """Validate required env vars on plugin load."""
        import os
        missing = [v for v in ("LINKEDIN_ACCESS_TOKEN",) if not os.environ.get(v)]
        if missing:
            import logging
            logging.getLogger(__name__).warning(
                "%s plugin loaded without %s — tool calls will fail until set",
                self.__class__.__name__, ", ".join(missing),
            )

    def _client(self) -> McpClient:
        return McpClient("linkedin-ads", self.kernel.root)

    def _proxy(self, tool: str, arguments: dict[str, Any]) -> str:
        """Call a tool on the external MCP server via stdio."""
        try:
            result = self._client().call_tool(tool, arguments)
            return result if isinstance(result, str) else json.dumps(result, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": "LinkedinAdsPlugin MCP call failed: " + str(exc)})

    def linkedin_ads_list_campaigns(self, account_id: str) -> str:
        """List campaigns."""
        return self._proxy("list_campaigns", {"account_id": account_id})

    def linkedin_ads_create_campaign(self, account_id: str, name: str, objective: str) -> str:
        """Create a campaign."""
        return self._proxy("create_campaign", {"account_id": account_id, "name": name, "objective": objective})

    def linkedin_ads_get_analytics(self, account_id: str, campaign_id: str) -> str:
        """Get analytics."""
        return self._proxy("get_analytics", {"account_id": account_id, "campaign_id": campaign_id})

    def linkedin_ads_list_ads(self, account_id: str, campaign_id: str) -> str:
        """List ads."""
        return self._proxy("list_ads", {"account_id": account_id, "campaign_id": campaign_id})

    def linkedin_ads_create_ad(self, account_id: str, campaign_id: str, name: str) -> str:
        """Create an ad."""
        return self._proxy("create_ad", {"account_id": account_id, "campaign_id": campaign_id, "name": name})

    def linkedin_ads_get_audiences(self, account_id: str) -> str:
        """Get audiences."""
        return self._proxy("get_audiences", {"account_id": account_id})

    def register_mcp_tools(self) -> list[Callable[..., str]]:
        return [
            self.linkedin_ads_list_campaigns,
            self.linkedin_ads_create_campaign,
            self.linkedin_ads_get_analytics,
            self.linkedin_ads_list_ads,
            self.linkedin_ads_create_ad,
            self.linkedin_ads_get_audiences
        ]
