"""Tests for aizee_mcp/rbac.py — RBAC permission checks and fail-closed behavior."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from aizee_mcp import rbac
from aizee_mcp.rbac import (
    _RBAC_BROKEN_SENTINEL,
    ADMIN_ROLE,
    _load_admin_required,
    check_tool_permission,
)

ADMIN_TOOL = "run_workflow"
NON_ADMIN_TOOL = "get_status"


# ---------------------------------------------------------------------------
# check_tool_permission — role combinations
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_no_roles_allows_everything() -> None:
    """Default-allow: when no roles are configured, all tools are allowed."""
    with patch.object(rbac, "_ADMIN_REQUIRED", frozenset({ADMIN_TOOL})):
        assert check_tool_permission(ADMIN_TOOL, set()) is True
        assert check_tool_permission(NON_ADMIN_TOOL, set()) is True


@pytest.mark.unit
def test_user_role_non_admin_tool_allowed() -> None:
    """Non-admin tools are allowed for any role."""
    with patch.object(rbac, "_ADMIN_REQUIRED", frozenset({ADMIN_TOOL})):
        assert check_tool_permission(NON_ADMIN_TOOL, {"user"}) is True


@pytest.mark.unit
def test_user_role_admin_tool_denied() -> None:
    """Admin tools are denied for non-admin roles."""
    with patch.object(rbac, "_ADMIN_REQUIRED", frozenset({ADMIN_TOOL})):
        assert check_tool_permission(ADMIN_TOOL, {"user"}) is False


@pytest.mark.unit
def test_admin_role_admin_tool_allowed() -> None:
    """Admin tools are allowed for the admin role."""
    with patch.object(rbac, "_ADMIN_REQUIRED", frozenset({ADMIN_TOOL})):
        assert check_tool_permission(ADMIN_TOOL, {"admin"}) is True


@pytest.mark.unit
def test_admin_plus_user_admin_tool_allowed() -> None:
    """Admin tools are allowed when admin is among the caller's roles."""
    with patch.object(rbac, "_ADMIN_REQUIRED", frozenset({ADMIN_TOOL})):
        assert check_tool_permission(ADMIN_TOOL, {"admin", "user"}) is True


@pytest.mark.unit
def test_non_admin_tool_allowed_for_admin() -> None:
    """Non-admin tools are allowed for the admin role too."""
    with patch.object(rbac, "_ADMIN_REQUIRED", frozenset({ADMIN_TOOL})):
        assert check_tool_permission(NON_ADMIN_TOOL, {"admin"}) is True


# ---------------------------------------------------------------------------
# _load_admin_required — missing / corrupted / valid config
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_load_admin_required_missing_file(tmp_path: Path) -> None:
    """A missing rbac.yaml means no admin restrictions (first-run scenario)."""
    result = _load_admin_required(tmp_path / "nonexistent.yaml")
    assert result == frozenset()


@pytest.mark.unit
def test_load_admin_required_valid_config(tmp_path: Path) -> None:
    """A valid rbac.yaml returns a frozenset of admin-required tool names."""
    config = tmp_path / "rbac.yaml"
    config.write_text("admin_required:\n  - run_workflow\n  - saga_run\n", encoding="utf-8")
    result = _load_admin_required(config)
    assert result == frozenset({"run_workflow", "saga_run"})


@pytest.mark.unit
def test_load_admin_required_corrupted_config(tmp_path: Path) -> None:
    """A corrupted rbac.yaml returns the broken sentinel (fail-closed)."""
    config = tmp_path / "rbac.yaml"
    config.write_text("{{invalid yaml: : :}", encoding="utf-8")
    result = _load_admin_required(config)
    assert result is _RBAC_BROKEN_SENTINEL


@pytest.mark.unit
def test_load_admin_required_empty_file(tmp_path: Path) -> None:
    """An empty rbac.yaml returns an empty frozenset (no admin restrictions)."""
    config = tmp_path / "rbac.yaml"
    config.write_text("", encoding="utf-8")
    result = _load_admin_required(config)
    assert result == frozenset()


@pytest.mark.unit
def test_load_admin_required_no_admin_required_key(tmp_path: Path) -> None:
    """A yaml without the admin_required key returns an empty frozenset."""
    config = tmp_path / "rbac.yaml"
    config.write_text("other_key: value\n", encoding="utf-8")
    result = _load_admin_required(config)
    assert result == frozenset()


# ---------------------------------------------------------------------------
# Fail-closed behavior when rbac.yaml is corrupted
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_fail_closed_denies_non_admin() -> None:
    """When rbac is broken, non-admin roles are denied all tools."""
    with patch.object(rbac, "_ADMIN_REQUIRED", _RBAC_BROKEN_SENTINEL):
        assert check_tool_permission(ADMIN_TOOL, {"user"}) is False
        assert check_tool_permission(NON_ADMIN_TOOL, {"user"}) is False


@pytest.mark.unit
def test_fail_closed_allows_admin() -> None:
    """When rbac is broken, the admin role is still allowed."""
    with patch.object(rbac, "_ADMIN_REQUIRED", _RBAC_BROKEN_SENTINEL):
        assert check_tool_permission(ADMIN_TOOL, {"admin"}) is True
        assert check_tool_permission(NON_ADMIN_TOOL, {"admin"}) is True


@pytest.mark.unit
def test_fail_closed_denies_no_roles() -> None:
    """When rbac is broken and no roles are set, all tools are denied."""
    with patch.object(rbac, "_ADMIN_REQUIRED", _RBAC_BROKEN_SENTINEL):
        assert check_tool_permission(ADMIN_TOOL, set()) is False
        assert check_tool_permission(NON_ADMIN_TOOL, set()) is False


# ---------------------------------------------------------------------------
# Admin tools denied for non-admin / non-admin tools allowed for any role
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_admin_tools_denied_for_multiple_non_admin_roles() -> None:
    """Admin tools are denied even when the caller has multiple non-admin roles."""
    with patch.object(rbac, "_ADMIN_REQUIRED", frozenset({ADMIN_TOOL, "saga_run", "chat"})):
        assert check_tool_permission(ADMIN_TOOL, {"user", "editor", "viewer"}) is False
        assert check_tool_permission("saga_run", {"user", "editor"}) is False
        assert check_tool_permission("chat", {"viewer"}) is False


@pytest.mark.unit
def test_non_admin_tools_allowed_for_any_role() -> None:
    """Non-admin tools are allowed regardless of the caller's role."""
    with patch.object(rbac, "_ADMIN_REQUIRED", frozenset({ADMIN_TOOL})):
        for role in ("user", "editor", "viewer", "guest", ADMIN_ROLE):
            assert check_tool_permission(NON_ADMIN_TOOL, {role}) is True
