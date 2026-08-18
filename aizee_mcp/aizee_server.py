#!/usr/bin/env python3
"""aiZee MCP server using FastMCP.

This is a thin entry point that creates the FastMCP instance and delegates
tool registration to the modules in ``aizee_mcp.tools``.
"""

from __future__ import annotations

import importlib
import pkgutil
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


def _auto_discover_tools() -> bool:
    """Scan ``aizee_mcp/tools/`` for ``*_tools.py`` modules and register them.

    Each module must expose a ``register`` callable (or a ``register_*_tools``
    function) that accepts the FastMCP instance. Returns True if at least one
    module was registered successfully, False otherwise.
    """
    import aizee_mcp.tools as tools_pkg

    registered = 0
    for module_info in pkgutil.iter_modules(tools_pkg.__path__):
        name = module_info.name
        if not name.endswith("_tools"):
            continue
        try:
            mod = importlib.import_module(f"aizee_mcp.tools.{name}")
        except Exception:
            continue
        # Prefer a no-arg ``register`` alias; fall back to ``register_*_tools``.
        register_fn = getattr(mod, "register", None)
        if register_fn is None:
            # Find a function matching register_*_tools pattern.
            for attr_name in dir(mod):
                if attr_name.startswith("register_") and attr_name.endswith("_tools"):
                    candidate = getattr(mod, attr_name)
                    if callable(candidate):
                        register_fn = candidate
                        break
        if register_fn is not None and callable(register_fn):
            try:
                register_fn(mcp)
                registered += 1
            except Exception:
                continue
    return registered > 0


def _register_tools_fallback() -> None:
    """Manual registration fallback when auto-discovery fails."""
    register_memory_tools(mcp)
    register_workflow_tools(mcp)
    register_policy_tools(mcp)
    register_context_tools(mcp)


# Auto-discover and register all tool modules; fall back to manual registration.
if not _auto_discover_tools():
    _register_tools_fallback()

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


def _graceful_shutdown(signum: int, frame: Any) -> None:
    try:
        from runtime.storage_backend import StorageFactory
        StorageFactory().shutdown_all()
    except Exception:
        pass
    raise SystemExit(0)


if __name__ == "__main__":
    import signal

    signal.signal(signal.SIGTERM, _graceful_shutdown)
    signal.signal(signal.SIGINT, _graceful_shutdown)
    mcp.run(transport="stdio")
