#!/usr/bin/env python3
"""Tests for runtime/mcp_securable.py — governed MCP server assets."""

from __future__ import annotations

import pytest

from runtime.mcp_securable import (
    Grant,
    McpPermission,
    McpSecurableRegistry,
    McpServer,
)


def _registry() -> McpSecurableRegistry:
    reg = McpSecurableRegistry()
    reg.register_server(McpServer(server_id="fs", name="Filesystem", endpoint="http://localhost:9000", allowed_tools=["read"]))
    return reg


class TestAdminImpliesUse:
    def test_admin_can_use(self) -> None:
        reg = _registry()
        reg.grant(Grant(server_id="fs", principal="alice", permission=McpPermission.ADMIN))
        assert reg.check_permission("fs", "alice", McpPermission.USE) is True

    def test_use_does_not_imply_admin(self) -> None:
        reg = _registry()
        reg.grant(Grant(server_id="fs", principal="bob", permission=McpPermission.USE))
        assert reg.check_permission("fs", "bob", McpPermission.ADMIN) is False


class TestOrphanGrants:
    def test_grant_on_unknown_server_raises(self) -> None:
        reg = McpSecurableRegistry()
        with pytest.raises(ValueError, match="unknown server"):
            reg.grant(Grant(server_id="ghost", principal="alice", permission=McpPermission.USE))

    def test_grant_empty_principal_raises(self) -> None:
        reg = _registry()
        with pytest.raises(ValueError, match="principal"):
            reg.grant(Grant(server_id="fs", principal="", permission=McpPermission.USE))


class TestCheckToolUse:
    def test_full_gate(self) -> None:
        reg = _registry()
        reg.grant(Grant(server_id="fs", principal="alice", permission=McpPermission.USE))
        assert reg.check_tool_use("fs", "alice", "read") is True
        assert reg.check_tool_use("fs", "alice", "write") is False  # not allowlisted
        assert reg.check_tool_use("fs", "mallory", "read") is False  # no grant
        assert reg.check_tool_use("ghost", "alice", "read") is False  # no server
