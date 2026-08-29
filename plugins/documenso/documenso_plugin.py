#!/usr/bin/env python3
"""DocumensoPlugin for aiZee — proxies to external MCP server.

External MCP server: npx -y @documenso/mcp
Required env vars: DOCUMENSO_API_KEY
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from runtime.mcp_client import McpClient
from runtime.plugin import AIOSPlugin


class DocumensoPlugin(AIOSPlugin):
    """Bridge AIOS kernel to the external documenso MCP server."""

    name = "documenso"
    version = "0.1.0"

    def on_load(self) -> None:
        """Validate required env vars on plugin load."""
        import os
        missing = [v for v in ("DOCUMENSO_API_KEY",) if not os.environ.get(v)]
        if missing:
            import logging
            logging.getLogger(__name__).warning(
                "%s plugin loaded without %s — tool calls will fail until set",
                self.__class__.__name__, ", ".join(missing),
            )

    def _client(self) -> McpClient:
        return McpClient("documenso", self.kernel.root)

    def _proxy(self, tool: str, arguments: dict[str, Any]) -> str:
        """Call a tool on the external MCP server via stdio."""
        try:
            result = self._client().call_tool(tool, arguments)
            return result if isinstance(result, str) else json.dumps(result, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": "DocumensoPlugin MCP call failed: " + str(exc)})

    def documenso_list_documents(self, limit: int = 10) -> str:
        """List documents."""
        return self._proxy("list_documents", {"limit": limit})

    def documenso_get_document(self, document_id: str) -> str:
        """Get a document by id."""
        return self._proxy("get_document", {"document_id": document_id})

    def documenso_create_document(self, title: str, file_url: str) -> str:
        """Create a document."""
        return self._proxy("create_document", {"title": title, "file_url": file_url})

    def documenso_send_signing_request(self, document_id: str, signer_email: str) -> str:
        """Send a signing request."""
        return self._proxy("send_signing_request", {"document_id": document_id, "signer_email": signer_email})

    def documenso_get_template(self, template_id: str) -> str:
        """Get a template."""
        return self._proxy("get_template", {"template_id": template_id})

    def documenso_create_template(self, title: str) -> str:
        """Create a template."""
        return self._proxy("create_template", {"title": title})

    def register_mcp_tools(self) -> list[Callable[..., str]]:
        return [
            self.documenso_list_documents,
            self.documenso_get_document,
            self.documenso_create_document,
            self.documenso_send_signing_request,
            self.documenso_get_template,
            self.documenso_create_template
        ]
