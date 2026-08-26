#!/usr/bin/env python3
"""Compatibility shim for the MCP Python SDK rename.

The ``mcp`` package renamed ``FastMCP`` to ``MCPServer`` and moved
``Resource`` to ``mcp.types`` in a recent release. aiZee source and tests
still import ``from mcp.server.fastmcp import FastMCP``. This module
re-exports the new symbols under the old names so existing imports keep
working without a tree-wide rewrite.

Usage::

    from aizee_mcp._compat import FastMCP, Resource

When the upstream package restores the old names (or aiZee migrates fully
to ``MCPServer``), this shim can be deleted and imports updated.
"""

from __future__ import annotations

from typing import Any, cast

# mypy: ignore-errors
# ruff: noqa: I001
try:
    from mcp.server.mcpserver import MCPServer as _FastMCPImpl  # pyright: ignore[import-error,reportMissingImports]
except ImportError:  # pragma: no cover - fallback for older mcp versions
    from mcp.server.fastmcp import FastMCP as _FastMCPImpl  # pyright: ignore[import-error,reportMissingImports]

try:
    from mcp.server.mcpserver.resources.base import Resource as _ResourceImpl  # pyright: ignore[import-error,reportMissingImports]
except ImportError:  # pragma: no cover - fallback for older mcp versions
    from mcp.server.fastmcp.resources import Resource as _ResourceImpl  # pyright: ignore[import-error,reportMissingImports]

try:
    from mcp.server.mcpserver.resources import FunctionResource as _FunctionResourceImpl  # pyright: ignore[import-error,reportMissingImports]
except ImportError:  # pragma: no cover - fallback for older mcp versions
    from mcp.server.fastmcp.resources import FunctionResource as _FunctionResourceImpl  # pyright: ignore[import-error,reportMissingImports]

# Cast to Any so downstream attribute access (add_tool, run, etc.) is
# permissive for both Pyright and mypy. The real classes are loaded above.
FastMCP = cast(Any, _FastMCPImpl)
Resource = cast(Any, _ResourceImpl)
FunctionResource = cast(Any, _FunctionResourceImpl)

__all__ = ["FastMCP", "FunctionResource", "Resource"]
