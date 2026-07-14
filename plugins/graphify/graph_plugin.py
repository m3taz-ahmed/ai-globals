#!/usr/bin/env python3
"""Graphify plugin for AI Global OS."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any

from runtime.plugin import AIOSPlugin


class GraphifyPlugin(AIOSPlugin):
    """Integrates graphify topological insights into AIOS memory."""

    name = "graphify"
    version = "0.1.0"

    def on_load(self) -> None:
        """Plugin initialization hook; graph data is read on demand."""

    def _graph_path(self) -> Path:
        return self.kernel.root / "graphify-out" / "graph.json"

    def _load_graph(self) -> dict[str, Any] | None:
        path = self._graph_path()
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        if not isinstance(data, dict):
            return None
        return data

    def _build_index(
        self, graph: dict[str, Any]
    ) -> tuple[dict[str, dict[str, Any]], dict[str, set[str]], dict[str, int]]:
        """Return (node_by_id, adjacency, degrees)."""
        nodes = graph.get("nodes", [])
        links = graph.get("links", [])
        node_by_id = {n["id"]: n for n in nodes if isinstance(n, dict) and "id" in n}
        adjacency: dict[str, set[str]] = defaultdict(set)
        degrees: Counter[str] = Counter()

        for link in links:
            if not isinstance(link, dict):
                continue
            source = link.get("source")
            target = link.get("target")
            if not isinstance(source, str) or not isinstance(target, str):
                continue
            if source not in node_by_id or target not in node_by_id:
                continue
            adjacency[source].add(target)
            adjacency[target].add(source)
            degrees[source] += 1
            degrees[target] += 1

        return node_by_id, dict(adjacency), dict(degrees)

    def _is_file_node(self, node: dict[str, Any]) -> bool:
        """Return True if the node represents a source file."""
        source_file = node.get("source_file", "")
        label = node.get("label", "")
        if not isinstance(source_file, str) or not isinstance(label, str):
            return False
        return label == Path(source_file).name

    def _neighborhood(
        self, node_by_id: dict[str, dict[str, Any]], adjacency: dict[str, set[str]], start_ids: list[str], depth: int
    ) -> dict[str, Any]:
        """BFS neighborhood up to ``depth`` edges from ``start_ids``."""
        visited: set[str] = set(start_ids)
        frontier: set[str] = set(start_ids)
        edges: list[dict[str, Any]] = []

        for _ in range(max(depth, 0)):
            next_frontier: set[str] = set()
            for node_id in frontier:
                for neighbor in adjacency.get(node_id, set()):
                    edges.append({"source": node_id, "target": neighbor})
                    if neighbor not in visited:
                        visited.add(neighbor)
                        next_frontier.add(neighbor)
            frontier = next_frontier
            if not frontier:
                break

        return {
            "nodes": [node_by_id[n] for n in visited if n in node_by_id],
            "edges": edges,
        }

    def query_graphify(self, query: str, depth: int = 1) -> str:
        """Return the topological neighborhood for a component or file."""
        graph = self._load_graph()
        if graph is None:
            return json.dumps({"ok": False, "error": "graphify-out/graph.json not found"})

        node_by_id, adjacency, _ = self._build_index(graph)
        query_lower = query.lower()
        matches = [
            node_id
            for node_id, node in node_by_id.items()
            if query_lower in str(node.get("label", "")).lower()
            or query_lower in str(node.get("norm_label", "")).lower()
            or query_lower in str(node.get("source_file", "")).lower()
        ]

        if not matches:
            return json.dumps({"ok": False, "error": f"No node matched '{query}'"})

        result = self._neighborhood(node_by_id, adjacency, matches, depth)
        return json.dumps({"ok": True, "query": query, "matches": len(matches), **result})

    def _god_nodes_summary(self, node_by_id: dict[str, dict[str, Any]], degrees: dict[str, int], top_n: int = 10) -> str:
        file_nodes = [(node_id, node, degrees.get(node_id, 0)) for node_id, node in node_by_id.items() if self._is_file_node(node)]
        top_files = sorted(file_nodes, key=lambda x: x[2], reverse=True)[:top_n]
        parts = [f"{node['label']!s} (degree={degree})" for node_id, node, degree in top_files]
        return "Graphify core architecture (God Nodes): " + ", ".join(parts)

    def _community_summaries(self, node_by_id: dict[str, dict[str, Any]], top_n: int = 5) -> list[str]:
        communities: dict[int, list[str]] = defaultdict(list)
        for node in node_by_id.values():
            if not self._is_file_node(node):
                continue
            community = node.get("community")
            if isinstance(community, int):
                communities[community].append(str(node.get("label", "")))

        sorted_communities = sorted(communities.items(), key=lambda kv: len(kv[1]), reverse=True)[:top_n]
        summaries: list[str] = []
        for community, labels in sorted_communities:
            clean = sorted({label for label in labels if label})
            summaries.append(
                f"Graphify community {community}: {len(clean)} files including " + ", ".join(clean[:10])
                + (" ..." if len(clean) > 10 else "")
            )
        return summaries

    def sync_graph_to_memory(self) -> str:
        """Convert graph topology into searchable semantic memory."""
        if self.memory is None:
            return json.dumps({"ok": False, "error": "Memory store not available"})

        graph = self._load_graph()
        if graph is None:
            return json.dumps({"ok": False, "error": "graphify-out/graph.json not found"})

        node_by_id, _, degrees = self._build_index(graph)
        added: list[str] = []

        summary = self._god_nodes_summary(node_by_id, degrees)
        mem = self.memory.add(kind="semantic", content=summary, source="graphify-sync")
        added.append(mem.id)

        for community_summary in self._community_summaries(node_by_id):
            mem = self.memory.add(kind="semantic", content=community_summary, source="graphify-sync")
            added.append(mem.id)

        return json.dumps({"ok": True, "added": len(added), "ids": added})

    def register_mcp_tools(self) -> list[Callable[..., str]]:
        return [self.query_graphify, self.sync_graph_to_memory]
