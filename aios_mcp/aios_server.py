#!/usr/bin/env python3
"""AI Global OS MCP server using FastMCP."""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

import config
from memory.store import MemoryStore
from runtime.kernel import Kernel

mcp = FastMCP("ai-global-os")
root = config.discover_root()
kernel = Kernel(root)
memory = MemoryStore(root)


@mcp.tool()
def query_rules(query: str) -> str:
    """Query AI Global OS rules by keyword."""
    results: list[dict[str, str]] = []
    for p in root.glob("rules/*.md"):
        content = p.read_text(encoding="utf-8")
        if query.lower() in content.lower():
            results.append({"file": str(p.relative_to(root)), "match": query})
    return json.dumps(results, indent=2)


@mcp.tool()
def run_workflow(id: str, context: dict[str, Any] | None = None) -> str:
    """Run a workflow by ID with optional context."""
    result = kernel.run_workflow(id, context or {})
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
def check_policy(action: str, args: dict[str, Any] | None = None) -> str:
    """Check if an action is allowed by policy and budget."""
    result = kernel.act(action, **(args or {}))
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
def search_memory(query: str, kind: str | None = None) -> str:
    """Search memory store by keyword and optional kind."""
    results = memory.search(query, kind)
    return json.dumps(
        [{"id": r.id, "kind": r.kind, "content": r.content[:500]} for r in results],
        indent=2,
    )


@mcp.tool()
def search_memory_vector(query: str, k: int = 5) -> str:
    """Search memory by vector similarity (requires sentence-transformers + turbovec)."""
    results = memory.search_vector(query, k=k)
    return json.dumps(results, indent=2)


@mcp.tool()
def get_related_memories(mem_id: str, relation: str | None = None) -> str:
    """Get memories related to the given memory ID."""
    results = memory.related(mem_id, relation)
    return json.dumps(
        [{"id": m.id, "kind": m.kind, "relation": r, "content": m.content[:500]} for m, r in results],
        indent=2,
    )


@mcp.tool()
def get_tech_stack(pkg: str, ver: str) -> str:
    """Get the tech-stack file for a package version."""
    path = root / "tech-stack" / f"{pkg}-{ver}.md"
    if not path.exists():
        return json.dumps({"exists": False, "path": str(path.relative_to(root))})
    return json.dumps({"exists": True, "path": str(path.relative_to(root)), "content": path.read_text(encoding="utf-8")})


@mcp.resource("rules://vocabulary")
def get_vocabulary() -> str:
    path = root / "rules" / "vocabulary.md"
    return path.read_text(encoding="utf-8") if path.exists() else ""


@mcp.resource("rules://anti-patterns")
def get_anti_patterns() -> str:
    path = root / "rules" / "anti-patterns.md"
    return path.read_text(encoding="utf-8") if path.exists() else ""


@mcp.resource("workflows://02-execution")
def get_execution_workflow() -> str:
    path = root / "workflows" / "02-execution.md"
    return path.read_text(encoding="utf-8") if path.exists() else ""


@mcp.resource("os://AGENTS")
def get_agents() -> str:
    path = root / "AGENTS.md"
    return path.read_text(encoding="utf-8") if path.exists() else ""


if __name__ == "__main__":
    mcp.run()
