#!/usr/bin/env python3
"""TwitterPlugin for aiZee — proxies to external MCP server.

External MCP server: npx -y @twitter-api-v2/mcp
Required env vars: TWITTER_BEARER_TOKEN
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from runtime.mcp_client import McpClient
from runtime.plugin import AIOSPlugin


class TwitterPlugin(AIOSPlugin):
    """Bridge AIOS kernel to the external twitter MCP server."""

    name = "twitter"
    version = "0.1.0"

    def on_load(self) -> None:
        """Validate required env vars on plugin load."""
        import os
        missing = [v for v in ("TWITTER_BEARER_TOKEN",) if not os.environ.get(v)]
        if missing:
            import logging
            logging.getLogger(__name__).warning(
                "%s plugin loaded without %s — tool calls will fail until set",
                self.__class__.__name__, ", ".join(missing),
            )

    def _client(self) -> McpClient:
        return McpClient("twitter", self.kernel.root)

    def _proxy(self, tool: str, arguments: dict[str, Any]) -> str:
        """Call a tool on the external MCP server via stdio."""
        try:
            result = self._client().call_tool(tool, arguments)
            return result if isinstance(result, str) else json.dumps(result, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": "TwitterPlugin MCP call failed: " + str(exc)})

    def twitter_post_tweet(self, text: str) -> str:
        """Post a tweet."""
        return self._proxy("post_tweet", {"text": text})

    def twitter_get_timeline(self, user: str) -> str:
        """Get a user timeline."""
        return self._proxy("get_timeline", {"user": user})

    def twitter_search(self, query: str) -> str:
        """Search tweets."""
        return self._proxy("search_tweets", {"query": query})

    def twitter_get_user(self, username: str) -> str:
        """Get user profile."""
        return self._proxy("get_user", {"username": username})

    def twitter_delete_tweet(self, tweet_id: str) -> str:
        """Delete a tweet."""
        return self._proxy("delete_tweet", {"tweet_id": tweet_id})

    def twitter_get_metrics(self, tweet_id: str) -> str:
        """Get tweet metrics."""
        return self._proxy("get_metrics", {"tweet_id": tweet_id})

    def register_mcp_tools(self) -> list[Callable[..., str]]:
        return [
            self.twitter_post_tweet,
            self.twitter_get_timeline,
            self.twitter_search,
            self.twitter_get_user,
            self.twitter_delete_tweet,
            self.twitter_get_metrics
        ]
