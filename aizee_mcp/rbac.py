#!/usr/bin/env python3
"""Explicit RBAC layer for aiZee MCP tools.

This is an additive, backward-compatible layer. By default (when the
``AIZEE_MCP_ROLES`` environment variable is unset or empty) every tool is
allowed for everyone, so existing behavior is preserved.

When roles ARE configured via ``AIZEE_MCP_ROLES`` (comma-separated), each tool
is allowed for the implicit ``user`` role EXCEPT those listed in
``aizee_mcp/rbac.yaml`` under ``admin_required``, which require the ``admin``
role.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Iterable
from pathlib import Path

import yaml

_logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path(__file__).with_name("rbac.yaml")
ADMIN_ROLE = "admin"
# Sentinel returned by _load_admin_required when rbac.yaml is corrupted.
# When this is the active set, check_tool_permission denies ALL tools.
_RBAC_BROKEN_SENTINEL = frozenset({"__rbac_broken__"})


def _load_admin_required(path: Path = DEFAULT_CONFIG_PATH) -> frozenset[str]:
    """Load the set of tool names that require the admin role.

    Fail-closed for parse errors: if the file exists but is unparsable, treat
    ALL tools as admin-required so a corrupted config cannot weaken security.
    A missing file is treated as "no admin restrictions" (first-run scenario).
    """
    try:
        if not path.exists():
            return frozenset()
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        items: Iterable[object] = raw.get("admin_required") or []
        return frozenset(str(item) for item in items)
    except Exception as exc:
        _logger.error(
            "RBAC config load failed (fail-closed): %s — all tools require admin",
            exc, exc_info=True,
        )
        # Return a sentinel that makes check_tool_permission deny everything.
        # We use a special marker recognized by check_tool_permission.
        return _RBAC_BROKEN_SENTINEL


_ADMIN_REQUIRED = _load_admin_required()


def get_roles_from_env() -> set[str]:
    """Derive the caller's roles from ``AIZEE_MCP_ROLES`` (comma-separated)."""
    raw = os.environ.get("AIZEE_MCP_ROLES", "")
    return {role.strip() for role in raw.split(",") if role.strip()}


def check_tool_permission(tool_name: str, roles: set[str] | None = None) -> bool:
    """Return True if ``roles`` may invoke ``tool_name``.

    - When ``roles`` is None it is read from ``AIZEE_MCP_ROLES``.
    - When no roles are configured (empty env) everything is allowed
      (default-allow, fully backward-compatible).
    - Otherwise, tools listed under ``admin_required`` in rbac.yaml require the
      ``admin`` role; all other tools are allowed for any role.
    - If rbac.yaml is corrupted (``_RBAC_BROKEN_SENTINEL``), ALL tools are
      denied unless the caller has the ``admin`` role (fail-closed).
    """
    if roles is None:
        roles = get_roles_from_env()
    # Fail-closed: corrupted config denies everything to non-admins
    if _ADMIN_REQUIRED is _RBAC_BROKEN_SENTINEL:
        return ADMIN_ROLE in roles if roles else False
    return not (roles and tool_name in _ADMIN_REQUIRED and ADMIN_ROLE not in roles)
