#!/usr/bin/env python3
"""Memory-related MCP tools."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from memory.graph import SchemaGraph
from memory.ingest import Ingestor

from .common import (
    _MAX_INPUT_LENGTH,
    _MAX_RESULTS,
    is_safe_name,
    memory,
    resolve_path,
    root,
    truncate,
    validate_kind,
    validate_query,
)


def register_memory_tools(mcp: FastMCP) -> None:
    """Register all memory-related MCP tools."""

    @mcp.tool()
    def search_memory(query: str, kind: str | None = None, limit: int = 20) -> str:
        """Search memory store by keyword and optional kind."""
        err = validate_query(query)
        if err:
            return err
        err = validate_kind(kind)
        if err:
            return err
        limit = max(1, min(limit, _MAX_RESULTS))
        results = memory().search(query, kind, limit=limit)
        return json.dumps(
            [{"id": r.id, "kind": r.kind, "source": r.source, "content": truncate(r.content)} for r in results],
            indent=2,
        )

    @mcp.tool()
    def search_memory_vector(query: str, k: int = 5, kind: str | None = None) -> str:
        """Search memory by vector similarity (requires sentence-transformers + turbovec)."""
        err = validate_query(query)
        if err:
            return err
        err = validate_kind(kind)
        if err:
            return err
        k = max(1, min(k, _MAX_RESULTS))
        results = memory().search_vector(query, k=k, kind=kind)
        return json.dumps(results, indent=2)

    @mcp.tool()
    def query_context(query: str, k: int = 5, kind: str | None = None) -> str:
        """Hybrid FTS + vector search across rules, tech-stack, workflows, and skills."""
        err = validate_query(query)
        if err:
            return err
        err = validate_kind(kind)
        if err:
            return err
        k = max(1, min(k, _MAX_RESULTS))
        store = memory()
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
                    "content": truncate(mem.content),
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
                    "content": truncate(record.content),
                    "fts": False,
                    "score": vr["score"],
                    "vector": True,
                }
            )

        return json.dumps(items, indent=2)

    @mcp.tool()
    def ingest_memory() -> str:
        """Ingest rules, tech-stack, workflows, skills, and AGENTS.md into memory."""
        ingestor = Ingestor(memory(), root())
        ids = ingestor.ingest_all()
        return json.dumps({"ingested": len(ids)}, indent=2)

    @mcp.tool()
    def get_related_memories(mem_id: str, relation: str | None = None) -> str:
        """Get memories related to the given memory ID."""
        if not isinstance(mem_id, str) or not mem_id or len(mem_id) > 128:
            return json.dumps({"ok": False, "error": "Invalid mem_id"})
        if relation is not None and not is_safe_name(relation):
            return json.dumps({"ok": False, "error": "Invalid relation"})
        results = memory().related(mem_id, relation)
        return json.dumps(
            [{"id": m.id, "kind": m.kind, "relation": r, "content": truncate(m.content)} for m, r in results],
            indent=2,
        )

    @mcp.tool()
    def add_memory(kind: str, content: str, source: str) -> str:
        """Add a new memory to the store."""
        if kind not in ["factual", "semantic", "episodic"]:
            return json.dumps({"ok": False, "error": "Invalid kind. Must be factual, semantic, or episodic."})
        if not isinstance(content, str) or not content or len(content) > _MAX_INPUT_LENGTH:
            return json.dumps({"ok": False, "error": "Invalid content"})
        if not isinstance(source, str) or not source or len(source) > 1024:
            return json.dumps({"ok": False, "error": "Invalid source"})
        mem = memory().add(kind, content, source=source)
        return json.dumps({"ok": True, "id": mem.id})

    @mcp.tool()
    def invalidate_memory(id: str) -> str:
        """Invalidate (deprecate) a memory by ID."""
        if not isinstance(id, str) or not id or len(id) > 128:
            return json.dumps({"ok": False, "error": "Invalid id"})
        store = memory()
        if store.get(id) is None:
            return json.dumps({"ok": False, "error": "Memory not found"})
        store.invalidate(id)
        return json.dumps({"ok": True, "id": id})

    @mcp.tool()
    def build_schema_graph(db_path: str) -> str:
        """Build a knowledge graph from a SQLite database schema."""
        if not isinstance(db_path, str) or not db_path or len(db_path) > 1024:
            return json.dumps({"ok": False, "error": "Invalid db_path"})
        r = root()
        target = resolve_path(r, Path(db_path))
        if target is None or not target.exists():
            return json.dumps({"ok": False, "error": "Database not found"})
        graph = SchemaGraph(str(target)).build()
        return json.dumps(
            {"ok": True, "nodes": len(graph.nodes), "edges": len(graph.edges), "nodes_list": [n.id for n in graph.nodes]},
            indent=2,
        )
