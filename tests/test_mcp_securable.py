"""Tests for runtime/mcp_securable.py — MCP server securables + RBAC grants.

Covers: enums, dataclasses, registry CRUD, grant/revoke, permission
checks, tool gating, filtering, thread safety, clear.
AAA pattern, one behavior per test. FAST tier — no MCP, no kernel.
"""

from __future__ import annotations

import threading

import pytest

from runtime.mcp_securable import (
    Grant,
    McpPermission,
    McpSecurableRegistry,
    McpServer,
)


# -- enums ----------------------------------------------------------------


class TestMcpPermission:
    def test_values(self) -> None:
        assert McpPermission.USE.value == "use"
        assert McpPermission.ADMIN.value == "admin"
        assert McpPermission.REGISTER.value == "register"

    def test_is_str(self) -> None:
        assert isinstance(McpPermission.USE, str)


# -- dataclasses ----------------------------------------------------------


class TestMcpServer:
    def test_defaults(self) -> None:
        server = McpServer(
            server_id="s1", name="S1", endpoint="http://x",
        )
        assert server.allowed_tools == []
        assert server.owner == ""


class TestGrant:
    def test_defaults(self) -> None:
        grant = Grant(
            server_id="s1", principal="alice", permission=McpPermission.USE,
        )
        assert grant.granted_by == ""


# -- fixtures -------------------------------------------------------------


@pytest.fixture
def registry() -> McpSecurableRegistry:
    return McpSecurableRegistry()


@pytest.fixture
def populated_registry() -> McpSecurableRegistry:
    reg = McpSecurableRegistry()
    reg.register_server(McpServer(
        server_id="fs", name="Filesystem",
        endpoint="http://localhost:9000",
        allowed_tools=["read", "write"], owner="ops",
    ))
    reg.register_server(McpServer(
        server_id="git", name="Git",
        endpoint="http://localhost:9001", allowed_tools=["log"],
    ))
    reg.grant(Grant(
        server_id="fs", principal="alice", permission=McpPermission.USE,
        granted_by="bob",
    ))
    reg.grant(Grant(
        server_id="fs", principal="alice", permission=McpPermission.ADMIN,
    ))
    reg.grant(Grant(
        server_id="git", principal="carol", permission=McpPermission.USE,
    ))
    return reg


# -- server CRUD ----------------------------------------------------------


class TestServerCrud:
    def test_register_and_get(self, registry: McpSecurableRegistry) -> None:
        server = McpServer(
            server_id="s1", name="S1", endpoint="http://x",
        )
        registry.register_server(server)
        assert registry.get_server("s1") is server

    def test_get_missing_returns_none(self, registry: McpSecurableRegistry) -> None:
        assert registry.get_server("nope") is None

    def test_register_replaces(self, registry: McpSecurableRegistry) -> None:
        registry.register_server(McpServer(
            server_id="s1", name="Old", endpoint="http://x",
        ))
        registry.register_server(McpServer(
            server_id="s1", name="New", endpoint="http://y",
        ))
        got = registry.get_server("s1")
        assert got is not None and got.name == "New"

    def test_list_servers(self, populated_registry: McpSecurableRegistry) -> None:
        ids = {s.server_id for s in populated_registry.list_servers()}
        assert ids == {"fs", "git"}


# -- grants ---------------------------------------------------------------


class TestGrants:
    def test_grant_and_check(self, registry: McpSecurableRegistry) -> None:
        registry.grant(Grant(
            server_id="s1", principal="alice", permission=McpPermission.USE,
        ))
        assert registry.check_permission("s1", "alice", McpPermission.USE) is True

    def test_check_permission_missing(self, registry: McpSecurableRegistry) -> None:
        assert registry.check_permission("s1", "alice", McpPermission.USE) is False

    def test_grant_is_idempotent(self, registry: McpSecurableRegistry) -> None:
        g = Grant(
            server_id="s1", principal="alice", permission=McpPermission.USE,
        )
        registry.grant(g)
        registry.grant(g)
        assert len(registry.list_grants("s1")) == 1

    def test_revoke_existing(self, registry: McpSecurableRegistry) -> None:
        registry.grant(Grant(
            server_id="s1", principal="alice", permission=McpPermission.USE,
        ))
        assert registry.revoke("s1", "alice", McpPermission.USE) is True
        assert registry.check_permission("s1", "alice", McpPermission.USE) is False

    def test_revoke_missing_returns_false(
        self, registry: McpSecurableRegistry,
    ) -> None:
        assert registry.revoke("s1", "alice", McpPermission.USE) is False

    def test_admin_does_not_imply_use(
        self, registry: McpSecurableRegistry,
    ) -> None:
        registry.grant(Grant(
            server_id="s1", principal="alice", permission=McpPermission.ADMIN,
        ))
        assert registry.check_permission("s1", "alice", McpPermission.USE) is False

    def test_list_grants_all(self, populated_registry: McpSecurableRegistry) -> None:
        assert len(populated_registry.list_grants()) == 3

    def test_list_grants_filtered_by_server(
        self, populated_registry: McpSecurableRegistry,
    ) -> None:
        grants = populated_registry.list_grants("fs")
        assert len(grants) == 2
        assert all(g.server_id == "fs" for g in grants)


# -- tool gating ----------------------------------------------------------


class TestToolGating:
    def test_is_tool_allowed_true(
        self, populated_registry: McpSecurableRegistry,
    ) -> None:
        assert populated_registry.is_tool_allowed("fs", "read") is True

    def test_is_tool_allowed_not_in_list(
        self, populated_registry: McpSecurableRegistry,
    ) -> None:
        assert populated_registry.is_tool_allowed("fs", "exec") is False

    def test_is_tool_allowed_missing_server(
        self, registry: McpSecurableRegistry,
    ) -> None:
        assert registry.is_tool_allowed("nope", "read") is False


# -- clear ----------------------------------------------------------------


class TestClear:
    def test_clear_removes_servers_and_grants(
        self, populated_registry: McpSecurableRegistry,
    ) -> None:
        populated_registry.clear()
        assert populated_registry.list_servers() == []
        assert populated_registry.list_grants() == []


# -- thread safety --------------------------------------------------------


class TestThreadSafety:
    def test_concurrent_grants(self) -> None:
        reg = McpSecurableRegistry()
        reg.register_server(McpServer(
            server_id="s1", name="S1", endpoint="http://x",
        ))
        n_threads = 20
        per_thread = 50

        def worker(tid: int) -> None:
            for i in range(per_thread):
                reg.grant(Grant(
                    server_id="s1", principal=f"p{tid}-{i}",
                    permission=McpPermission.USE,
                ))

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(reg.list_grants()) == n_threads * per_thread
