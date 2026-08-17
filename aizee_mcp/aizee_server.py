#!/usr/bin/env python3
"""aiZee MCP server using FastMCP.

This is a thin entry point that creates the FastMCP instance and delegates
tool registration to the modules in ``aizee_mcp.tools``.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from aizee_mcp.tools import (
    register_context_tools,
    register_memory_tools,
    register_policy_tools,
    register_workflow_tools,
)
from aizee_mcp.tools.common import kernel, reset_state  # noqa: F401 — re-exported for tests

mcp = FastMCP("aizee")


def _register_plugins() -> None:
    """Load enabled plugins and register their MCP tools/resources."""
    k = kernel()
    from aizee_mcp.tools.common import memory

    k.load_plugins(memory())
    for tool in k.plugins.get_tools():
        mcp.add_tool(tool)
    for resource in k.plugins.get_resources():
        mcp.add_resource(resource)


# Register all tool modules
register_memory_tools(mcp)
register_workflow_tools(mcp)
register_policy_tools(mcp)
register_context_tools(mcp)

_register_plugins()

# Backward-compatible aliases for tests that import directly from aizee_server.
# These reference the functions registered on the mcp instance.
# The tool functions are closures inside the register_* functions, so we
# expose them via the tool manager for backward compatibility.
_tool_manager = mcp._tool_manager


def _get_tool_fn(name: str) -> Any:
    """Get a registered tool function by name."""
    tool = _tool_manager.get_tool(name)
    return tool.fn if tool else None


# Resource functions are also closures; expose them for direct-call tests.
def get_rule_resource(id: str) -> str:
    fn = _get_tool_fn("get_rule_resource")
    if fn:
        return str(fn(id))
    # Fallback: look in resource registry
    from pathlib import Path

    from aizee_mcp.tools.common import is_safe_name, resolve_path, root

    if not is_safe_name(id):
        return ""
    r = root()
    path = resolve_path(r, Path("rules") / f"{id}.md")
    if path is None or not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def get_workflow_resource(id: str) -> str:
    from pathlib import Path

    from aizee_mcp.tools.common import is_safe_name, resolve_path, root

    if not is_safe_name(id):
        return ""
    r = root()
    path = resolve_path(r, Path("workflows") / f"{id}.md")
    if path is None or not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


if __name__ == "__main__":
    mcp.run(transport="stdio")
