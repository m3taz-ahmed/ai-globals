#!/usr/bin/env python3
"""GrowthbookPlugin for aiZee — proxies to external MCP server.

External MCP server: npx -y @growthbook/mcp
Required env vars: GROWTHBOOK_API_KEY
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from runtime.mcp_client import McpClient
from runtime.plugin import AIOSPlugin


class GrowthbookPlugin(AIOSPlugin):
    """Bridge AIOS kernel to the external growthbook MCP server."""

    name = "growthbook"
    version = "0.1.0"

    def on_load(self) -> None:
        """Validate required env vars on plugin load."""
        import os
        missing = [v for v in ("GROWTHBOOK_API_KEY",) if not os.environ.get(v)]
        if missing:
            import logging
            logging.getLogger(__name__).warning(
                "%s plugin loaded without %s — tool calls will fail until set",
                self.__class__.__name__, ", ".join(missing),
            )

    def _client(self) -> McpClient:
        return McpClient("growthbook", self.kernel.root)

    def _proxy(self, tool: str, arguments: dict[str, Any]) -> str:
        """Call a tool on the external MCP server via stdio."""
        try:
            result = self._client().call_tool(tool, arguments)
            return result if isinstance(result, str) else json.dumps(result, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": "GrowthbookPlugin MCP call failed: " + str(exc)})

    def growthbook_list_features(self) -> str:
        """List features (free-first)."""
        return self._proxy("list_features", {})

    def growthbook_get_feature(self, feature_id: str) -> str:
        """Get a feature."""
        return self._proxy("get_feature", {"feature_id": feature_id})

    def growthbook_create_feature(self, key: str, description: str = "") -> str:
        """Create a feature."""
        return self._proxy("create_feature", {"key": key, "description": description})

    def growthbook_list_experiments(self) -> str:
        """List experiments."""
        return self._proxy("list_experiments", {})

    def growthbook_get_experiment(self, experiment_id: str) -> str:
        """Get an experiment."""
        return self._proxy("get_experiment", {"experiment_id": experiment_id})

    def growthbook_get_metrics(self) -> str:
        """Get metrics."""
        return self._proxy("get_metrics", {})

    def register_mcp_tools(self) -> list[Callable[..., str]]:
        return [
            self.growthbook_list_features,
            self.growthbook_get_feature,
            self.growthbook_create_feature,
            self.growthbook_list_experiments,
            self.growthbook_get_experiment,
            self.growthbook_get_metrics
        ]
