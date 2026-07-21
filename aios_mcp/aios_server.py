#!/usr/bin/env python3
"""AI Global OS MCP server using FastMCP."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

import config
from memory.ingest import Ingestor
from memory.store import MemoryStore
from runtime.kernel import Kernel

mcp = FastMCP("ai-global-os")

_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")

_kernel_instance: Kernel | None = None
_memory_instance: MemoryStore | None = None
_current_root: Path | None = None


def _root() -> Path:
    """Discover root each call to react to env changes."""
    return config.discover_root()


def reset_state() -> None:
    """Reset cached kernel and memory instances. Useful for tests and env changes."""
    global _kernel_instance, _memory_instance, _current_root
    _kernel_instance = None
    _memory_instance = None
    _current_root = None


def _kernel() -> Kernel:
    """Return a Kernel instance, recreating if the discovered root changes."""
    global _kernel_instance, _current_root
    discovered = _root()
    if _kernel_instance is None or _current_root != discovered:
        _current_root = discovered
        _kernel_instance = Kernel(_current_root)
    return _kernel_instance


def _memory() -> MemoryStore:
    """Return a MemoryStore instance tied to the discovered root."""
    global _memory_instance
    discovered = _root()
    if _memory_instance is None or _memory_instance.root != discovered:
        _memory_instance = MemoryStore(discovered)
    return _memory_instance


def _is_safe_name(name: str) -> bool:
    return bool(_NAME_RE.fullmatch(name))


def _truncate(content: str, limit: int = 500) -> str:
    return content if len(content) <= limit else content[:limit] + "..."


def _register_plugins() -> None:
    """Load enabled plugins and register their MCP tools/resources."""
    kernel = _kernel()
    memory = _memory()
    kernel.load_plugins(memory)
    for tool in kernel.plugins.get_tools():
        mcp.add_tool(tool)
    for resource in kernel.plugins.get_resources():
        mcp.add_resource(resource)


@mcp.tool()
def query_rules(query: str) -> str:
    """Query AI Global OS rules by keyword."""
    root = _root()
    results: list[dict[str, str]] = []
    for p in root.glob("rules/*.md"):
        content = p.read_text(encoding="utf-8")
        if query.lower() in content.lower():
            results.append({"file": str(p.relative_to(root)), "match": query})
    return json.dumps(results, indent=2)


@mcp.tool()
def run_workflow(id: str, context: dict[str, Any] | None = None) -> str:
    """Run a workflow by ID with optional context."""
    result = _kernel().run_workflow(id, context or {})
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
def check_policy(action: str, args: dict[str, Any] | None = None) -> str:
    """Check if an action is allowed by policy and budget."""
    result = _kernel().act(action, **(args or {}))
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
def analyze_budget() -> str:
    """Analyze current token and cost consumption across all budgets and scopes."""
    kernel = _kernel()
    return json.dumps(
        {
            "usage": kernel.budget.usage,
            "budgets": {k: v.__dict__ for k, v in kernel.budget.budgets.items()}
        },
        indent=2,
        default=str
    )


@mcp.tool()
def search_memory(query: str, kind: str | None = None) -> str:
    """Search memory store by keyword and optional kind."""
    results = _memory().search(query, kind)
    return json.dumps(
        [{"id": r.id, "kind": r.kind, "source": r.source, "content": _truncate(r.content)} for r in results],
        indent=2,
    )


@mcp.tool()
def search_memory_vector(query: str, k: int = 5, kind: str | None = None) -> str:
    """Search memory by vector similarity (requires sentence-transformers + turbovec)."""
    results = _memory().search_vector(query, k=k, kind=kind)
    return json.dumps(results, indent=2)


@mcp.tool()
def query_context(query: str, k: int = 5, kind: str | None = None) -> str:
    """Hybrid FTS + vector search across rules, tech-stack, workflows, and skills."""
    store = _memory()
    fts_results = store.search(query, kind=kind, limit=k)
    vector_results = store.search_vector(query, k=k, kind=kind)

    seen: set[str] = set()
    items: list[dict[str, Any]] = []

    for mem in fts_results:
        seen.add(mem.id)
        items.append(
            {
                "id": mem.id,
                "kind": mem.kind,
                "source": mem.source,
                "content": _truncate(mem.content),
                "fts": True,
                "score": None,
            }
        )

    for vr in vector_results:
        mem_id = vr["id"]
        if mem_id in seen:
            for item in items:
                if item["id"] == mem_id:
                    item["score"] = vr["score"]
                    item["vector"] = True
            continue
        record = store.get(mem_id)
        if record is None:
            continue
        items.append(
            {
                "id": record.id,
                "kind": record.kind,
                "source": record.source,
                "content": _truncate(record.content),
                "fts": False,
                "score": vr["score"],
                "vector": True,
            }
        )

    return json.dumps(items, indent=2)


@mcp.tool()
def ingest_memory() -> str:
    """Ingest rules, tech-stack, workflows, skills, and AGENTS.md into memory."""
    ingestor = Ingestor(_memory(), _root())
    ids = ingestor.ingest_all()
    return json.dumps({"ingested": len(ids)}, indent=2)


@mcp.tool()
def get_related_memories(mem_id: str, relation: str | None = None) -> str:
    """Get memories related to the given memory ID."""
    results = _memory().related(mem_id, relation)
    return json.dumps(
        [{"id": m.id, "kind": m.kind, "relation": r, "content": _truncate(m.content)} for m, r in results],
        indent=2,
    )


@mcp.tool()
def add_memory(kind: str, content: str, source: str) -> str:
    """Add a new memory to the store."""
    if kind not in ["factual", "semantic", "episodic"]:
        return json.dumps({"ok": False, "error": "Invalid kind. Must be factual, semantic, or episodic."})
    mem = _memory().add(kind, content, source=source)
    return json.dumps({"ok": True, "id": mem.id})


@mcp.tool()
def invalidate_memory(id: str) -> str:
    """Invalidate (deprecate) a memory by ID."""
    store = _memory()
    if store.get(id) is None:
        return json.dumps({"ok": False, "error": "Memory not found"})
    store.invalidate(id)
    return json.dumps({"ok": True, "id": id})


@mcp.tool()
def get_tech_stack(pkg: str, ver: str) -> str:
    """Get the tech-stack file for a package version."""
    if not _is_safe_name(pkg) or not _is_safe_name(ver):
        return json.dumps({"ok": False, "error": "Invalid package or version name"})
    root = _root()
    path = root / "tech-stack" / f"{pkg}-{ver}.md"
    if not path.exists():
        return json.dumps({"exists": False, "path": str(path.relative_to(root))})
    return json.dumps({"exists": True, "path": str(path.relative_to(root)), "content": path.read_text(encoding="utf-8")})


@mcp.tool()
def list_rules() -> str:
    """List available rule files."""
    root = _root()
    results = [{"id": p.stem, "file": str(p.relative_to(root))} for p in sorted(root.glob("rules/*.md"))]
    return json.dumps(results, indent=2)


@mcp.tool()
def get_rule(id: str) -> str:
    """Get a rule file by its stem (id)."""
    if not _is_safe_name(id):
        return json.dumps({"ok": False, "error": "Invalid rule id"})
    root = _root()
    path = root / "rules" / f"{id}.md"
    if not path.exists():
        return json.dumps({"exists": False, "path": str(path.relative_to(root))})
    return json.dumps({"exists": True, "path": str(path.relative_to(root)), "content": path.read_text(encoding="utf-8")})


@mcp.tool()
def list_workflows() -> str:
    """List available workflow files."""
    root = _root()
    results = [{"id": p.stem, "file": str(p.relative_to(root))} for p in sorted(root.glob("workflows/*.md"))]
    return json.dumps(results, indent=2)


@mcp.tool()
def get_workflow(id: str) -> str:
    """Get a workflow file by its stem (id)."""
    if not _is_safe_name(id):
        return json.dumps({"ok": False, "error": "Invalid workflow id"})
    root = _root()
    path = root / "workflows" / f"{id}.md"
    if not path.exists():
        return json.dumps({"exists": False, "path": str(path.relative_to(root))})
    return json.dumps({"exists": True, "path": str(path.relative_to(root)), "content": path.read_text(encoding="utf-8")})


@mcp.resource("rules://{id}")
def get_rule_resource(id: str) -> str:
    if not _is_safe_name(id):
        return ""
    root = _root()
    path = root / "rules" / f"{id}.md"
    return path.read_text(encoding="utf-8") if path.exists() else ""


@mcp.resource("workflows://{id}")
def get_workflow_resource(id: str) -> str:
    if not _is_safe_name(id):
        return ""
    root = _root()
    path = root / "workflows" / f"{id}.md"
    return path.read_text(encoding="utf-8") if path.exists() else ""


@mcp.resource("os://AGENTS")
def get_agents() -> str:
    root = _root()
    path = root / "AGENTS.md"
    return path.read_text(encoding="utf-8") if path.exists() else ""


_register_plugins()


if __name__ == "__main__":
    mcp.run(transport="stdio")
