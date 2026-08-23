"""Register MCP servers as governed securable assets with RBAC grants.

Inspired by Databricks Unity Catalog: each MCP server is a securable
asset. Access is governed by explicit GRANT policies per principal +
permission. No implicit access — a principal must hold a matching grant.

Usage::

    from runtime.mcp_securable import (
        McpSecurableRegistry, McpServer, Grant, McpPermission,
    )

    reg = McpSecurableRegistry()
    reg.register_server(McpServer(
        server_id="fs", name="Filesystem",
        endpoint="http://localhost:9000", allowed_tools=["read", "write"],
    ))
    reg.grant(Grant(server_id="fs", principal="alice",
                    permission=McpPermission.USE))
    assert reg.check_permission("fs", "alice", McpPermission.USE) is True
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from enum import Enum


class McpPermission(str, Enum):
    """Permissions that may be granted on an MCP server securable."""

    USE = "use"
    ADMIN = "admin"
    REGISTER = "register"


@dataclass
class McpServer:
    """A registered MCP server securable."""

    server_id: str
    name: str
    endpoint: str
    allowed_tools: list[str] = field(default_factory=list)
    owner: str = ""


@dataclass
class Grant:
    """A permission grant of a principal on a server."""

    server_id: str
    principal: str
    permission: McpPermission
    granted_by: str = ""


class McpSecurableRegistry:
    """Thread-safe registry of MCP server securables and grants.

    Grants are keyed by ``(server_id, principal, permission)`` so a
    duplicate grant is idempotent. ``ADMIN`` does not implicitly imply
    ``USE`` — each permission must be granted explicitly.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._servers: dict[str, McpServer] = {}
        self._grants: dict[tuple[str, str, McpPermission], Grant] = {}

    # -- server registration --------------------------------------------

    def register_server(self, server: McpServer) -> None:
        """Register or replace a server by its ``server_id``."""
        with self._lock:
            self._servers[server.server_id] = server

    def get_server(self, server_id: str) -> McpServer | None:
        """Return the server with ``server_id`` or ``None``."""
        with self._lock:
            return self._servers.get(server_id)

    def list_servers(self) -> list[McpServer]:
        """List all registered servers."""
        with self._lock:
            return list(self._servers.values())

    # -- grants ----------------------------------------------------------

    def grant(self, grant: Grant) -> None:
        """Add a grant (idempotent for the same triple)."""
        with self._lock:
            self._grants[(grant.server_id, grant.principal, grant.permission)] = grant

    def revoke(
        self, server_id: str, principal: str, permission: McpPermission,
    ) -> bool:
        """Revoke a grant. Returns True if a grant was removed."""
        with self._lock:
            return self._grants.pop(
                (server_id, principal, permission), None,
            ) is not None

    def check_permission(
        self, server_id: str, principal: str, permission: McpPermission,
    ) -> bool:
        """True if the principal holds the permission on the server."""
        with self._lock:
            return (server_id, principal, permission) in self._grants

    def list_grants(self, server_id: str | None = None) -> list[Grant]:
        """List grants, optionally filtered by ``server_id``."""
        with self._lock:
            grants = list(self._grants.values())
        if server_id is None:
            return grants
        return [g for g in grants if g.server_id == server_id]

    # -- tool gating -----------------------------------------------------

    def is_tool_allowed(self, server_id: str, tool_name: str) -> bool:
        """True if the server exists and the tool is in its allowlist."""
        with self._lock:
            server = self._servers.get(server_id)
            if server is None:
                return False
            return tool_name in server.allowed_tools

    # -- maintenance -----------------------------------------------------

    def clear(self) -> None:
        """Remove all servers and grants."""
        with self._lock:
            self._servers.clear()
            self._grants.clear()


__all__ = [
    "Grant",
    "McpPermission",
    "McpSecurableRegistry",
    "McpServer",
]
