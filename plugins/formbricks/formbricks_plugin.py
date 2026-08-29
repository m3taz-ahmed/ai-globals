#!/usr/bin/env python3
"""FormbricksPlugin for aiZee — proxies to external MCP server.

External MCP server: npx -y @formbricks/mcp
Required env vars: FORMBRICKS_API_KEY
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from runtime.mcp_client import McpClient
from runtime.plugin import AIOSPlugin


class FormbricksPlugin(AIOSPlugin):
    """Bridge AIOS kernel to the external formbricks MCP server."""

    name = "formbricks"
    version = "0.1.0"

    def on_load(self) -> None:
        """Validate required env vars on plugin load."""
        import os
        missing = [v for v in ("FORMBRICKS_API_KEY",) if not os.environ.get(v)]
        if missing:
            import logging
            logging.getLogger(__name__).warning(
                "%s plugin loaded without %s — tool calls will fail until set",
                self.__class__.__name__, ", ".join(missing),
            )

    def _client(self) -> McpClient:
        return McpClient("formbricks", self.kernel.root)

    def _proxy(self, tool: str, arguments: dict[str, Any]) -> str:
        """Call a tool on the external MCP server via stdio."""
        try:
            result = self._client().call_tool(tool, arguments)
            return result if isinstance(result, str) else json.dumps(result, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": "FormbricksPlugin MCP call failed: " + str(exc)})

    def formbricks_list_surveys(self, limit: int = 10) -> str:
        """List surveys."""
        return self._proxy("list_surveys", {"limit": limit})

    def formbricks_get_survey(self, survey_id: str) -> str:
        """Get a survey."""
        return self._proxy("get_survey", {"survey_id": survey_id})

    def formbricks_create_survey(self, name: str, questions: str) -> str:
        """Create a survey."""
        return self._proxy("create_survey", {"name": name, "questions": questions})

    def formbricks_get_responses(self, survey_id: str, limit: int = 10) -> str:
        """Get responses."""
        return self._proxy("get_responses", {"survey_id": survey_id, "limit": limit})

    def formbricks_get_analytics(self, survey_id: str) -> str:
        """Get analytics."""
        return self._proxy("get_analytics", {"survey_id": survey_id})

    def formbricks_list_responses(self, limit: int = 10) -> str:
        """List all responses."""
        return self._proxy("list_responses", {"limit": limit})

    def register_mcp_tools(self) -> list[Callable[..., str]]:
        return [
            self.formbricks_list_surveys,
            self.formbricks_get_survey,
            self.formbricks_create_survey,
            self.formbricks_get_responses,
            self.formbricks_get_analytics,
            self.formbricks_list_responses
        ]
