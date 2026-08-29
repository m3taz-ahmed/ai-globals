#!/usr/bin/env python3
"""FlagsmithPlugin for aiZee — proxies to external MCP server.

External MCP server: npx -y @flagsmith/mcp
Required env vars: FLAGSMITH_API_KEY
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from runtime.mcp_client import McpClient
from runtime.plugin import AIOSPlugin


class FlagsmithPlugin(AIOSPlugin):
    """Bridge AIOS kernel to the external flagsmith MCP server."""

    name = "flagsmith"
    version = "0.1.0"

    def on_load(self) -> None:
        """Validate required env vars on plugin load."""
        import os
        missing = [v for v in ("FLAGSMITH_API_KEY",) if not os.environ.get(v)]
        if missing:
            import logging
            logging.getLogger(__name__).warning(
                "%s plugin loaded without %s — tool calls will fail until set",
                self.__class__.__name__, ", ".join(missing),
            )

    def _client(self) -> McpClient:
        return McpClient("flagsmith", self.kernel.root)

    def _proxy(self, tool: str, arguments: dict[str, Any]) -> str:
        """Call a tool on the external MCP server via stdio."""
        try:
            result = self._client().call_tool(tool, arguments)
            return result if isinstance(result, str) else json.dumps(result, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": "FlagsmithPlugin MCP call failed: " + str(exc)})

    def flagsmith_list_features(self) -> str:
        """List features (free-first)."""
        return self._proxy("list_features", {})

    def flagsmith_get_feature(self, feature_id: str) -> str:
        """Get a feature."""
        return self._proxy("get_feature", {"feature_id": feature_id})

    def flagsmith_create_feature(self, name: str, description: str = "") -> str:
        """Create a feature."""
        return self._proxy("create_feature", {"name": name, "description": description})

    def flagsmith_list_segments(self) -> str:
        """List segments."""
        return self._proxy("list_segments", {})

    def flagsmith_get_environment(self) -> str:
        """Get environment."""
        return self._proxy("get_environment", {})

    def flagsmith_create_trait(self, key: str, value: str) -> str:
        """Create a trait."""
        return self._proxy("create_trait", {"key": key, "value": value})

    def register_mcp_tools(self) -> list[Callable[..., str]]:
        return [
            self.flagsmith_list_features,
            self.flagsmith_get_feature,
            self.flagsmith_create_feature,
            self.flagsmith_list_segments,
            self.flagsmith_get_environment,
            self.flagsmith_create_trait
        ]
