#!/usr/bin/env python3
"""ChatwootPlugin for aiZee — proxies to external MCP server.

External MCP server: npx -y @chatwoot/mcp
Required env vars: CHATWOOT_API_KEY, CHATWOOT_URL
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from runtime.mcp_client import McpClient
from runtime.plugin import AIOSPlugin


class ChatwootPlugin(AIOSPlugin):
    """Bridge AIOS kernel to the external chatwoot MCP server."""

    name = "chatwoot"
    version = "0.1.0"

    def on_load(self) -> None:
        """Validate required env vars on plugin load."""
        import os
        missing = [v for v in ("CHATWOOT_API_KEY", "CHATWOOT_URL") if not os.environ.get(v)]
        if missing:
            import logging
            logging.getLogger(__name__).warning(
                "%s plugin loaded without %s — tool calls will fail until set",
                self.__class__.__name__, ", ".join(missing),
            )

    def _client(self) -> McpClient:
        return McpClient("chatwoot", self.kernel.root)

    def _proxy(self, tool: str, arguments: dict[str, Any]) -> str:
        """Call a tool on the external MCP server via stdio."""
        try:
            result = self._client().call_tool(tool, arguments)
            return result if isinstance(result, str) else json.dumps(result, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": "ChatwootPlugin MCP call failed: " + str(exc)})

    def chatwoot_list_conversations(self, account_id: str, limit: int = 10) -> str:
        """List conversations."""
        return self._proxy("list_conversations", {"account_id": account_id, "limit": limit})

    def chatwoot_get_messages(self, account_id: str, conversation_id: str) -> str:
        """Get messages."""
        return self._proxy("get_messages", {"account_id": account_id, "conversation_id": conversation_id})

    def chatwoot_send_message(self, account_id: str, conversation_id: str, text: str) -> str:
        """Send a message."""
        return self._proxy("send_message", {"account_id": account_id, "conversation_id": conversation_id, "text": text})

    def chatwoot_list_contacts(self, account_id: str, limit: int = 10) -> str:
        """List contacts."""
        return self._proxy("list_contacts", {"account_id": account_id, "limit": limit})

    def chatwoot_create_contact(self, account_id: str, name: str, email: str = "") -> str:
        """Create a contact."""
        return self._proxy("create_contact", {"account_id": account_id, "name": name, "email": email})

    def chatwoot_assign_agent(self, account_id: str, conversation_id: str, agent_id: str) -> str:
        """Assign an agent."""
        return self._proxy("assign_agent", {"account_id": account_id, "conversation_id": conversation_id, "agent_id": agent_id})

    def register_mcp_tools(self) -> list[Callable[..., str]]:
        return [
            self.chatwoot_list_conversations,
            self.chatwoot_get_messages,
            self.chatwoot_send_message,
            self.chatwoot_list_contacts,
            self.chatwoot_create_contact,
            self.chatwoot_assign_agent
        ]
