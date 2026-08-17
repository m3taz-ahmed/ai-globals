#!/usr/bin/env python3
"""Context7 plugin for aiZee — proxies to @upstash/context7-mcp.

Provides live library/framework documentation retrieval. Required by the
`mcp.mdc` rule: "Query Context7 MCP before writing external library/framework
code."
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from runtime.mcp_client import McpClient
from runtime.plugin import AIOSPlugin


class Context7Plugin(AIOSPlugin):
    """Bridge AIOS kernel to the external Context7 MCP server."""

    name = "context7"
    version = "0.1.0"

    def on_load(self) -> None:
        """No credentials required for Context7."""
        return None

    def _client(self) -> McpClient:
        return McpClient("context7", self.kernel.root)

    def resolve_library_id(self, library_name: str) -> str:
        """Resolve a library name to its Context7 library ID."""
        return self._proxy("resolve-library-id", {"libraryName": library_name})

    def get_library_docs(self, library_id: str, topic: str = "") -> str:
        """Get documentation for a library by its Context7 ID.

        Args:
            library_id: The resolved library ID from resolve_library_id.
            topic: Optional focus area (e.g. "authentication", "routing").
        """
        args: dict[str, Any] = {"context7LibraryId": library_id}
        if topic:
            args["topic"] = topic
        return self._proxy("get-library-docs", args)

    def _proxy(self, tool: str, arguments: dict[str, Any]) -> str:
        """Call a tool on the external Context7 MCP server via stdio."""
        try:
            result = self._client().call_tool(tool, arguments)
            return result if isinstance(result, str) else json.dumps(result, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": f"Context7 MCP call failed: {exc!s}"})

    def register_mcp_tools(self) -> list[Callable[..., str]]:
        return [self.resolve_library_id, self.get_library_docs]
