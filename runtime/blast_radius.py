#!/usr/bin/env python3
"""Blast radius graph for AI supply-chain security.

Inspired by agent-bom: tracks the propagation chain from a CVE through the
AI supply chain — ``CVE -> package -> MCP server -> agent -> credentials ->
tools``.  Each node represents an entity in the chain; edges represent
dependency / exposure relationships.  When a vulnerability is discovered,
:meth:`BlastRadiusGraph.trace` finds every path from the CVE node to
credential/tool nodes, and :meth:`BlastRadiusGraph.impact` computes the
aggregate blast-radius impact level.

The graph is directed and uses a dict-based adjacency list.  Path finding
uses BFS to avoid infinite loops on cyclic sub-graphs.  All public methods
are thread-safe via an :class:`threading.RLock`.

Usage::

    from runtime.blast_radius import BlastRadiusGraph, NodeType, ImpactLevel
    g = BlastRadiusGraph()
    cve = g.add_cve("CVE-2024-1234", "evil-pkg", "critical")
    pkg = g.add_package("evil-pkg", "1.2.3", "pypi")
    g.add_edge(BlastEdge(source_id=cve.node_id, target_id=pkg.node_id, relationship="affects"))
    paths = g.trace(cve.node_id)
    level = g.impact(cve.node_id)
"""

from __future__ import annotations

import logging
import threading
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from runtime.schemas import AizeeError, ErrorSeverity, ValidationError

_logger = logging.getLogger(__name__)


class NodeType(str, Enum):
    """Type of entity in the blast-radius chain."""

    CVE = "cve"
    PACKAGE = "package"
    MCP_SERVER = "mcp_server"
    AGENT = "agent"
    CREDENTIAL = "credential"
    TOOL = "tool"
    POLICY = "policy"


class ImpactLevel(str, Enum):
    """Aggregate impact level for a blast-radius path or node."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


# Numeric ordering for impact comparison (higher = worse).
_IMPACT_RANK: dict[ImpactLevel, int] = {
    ImpactLevel.NONE: 0,
    ImpactLevel.LOW: 1,
    ImpactLevel.MEDIUM: 2,
    ImpactLevel.HIGH: 3,
    ImpactLevel.CRITICAL: 4,
}

# Map external severity strings to ImpactLevel.
_SEVERITY_MAP: dict[str, ImpactLevel] = {
    "critical": ImpactLevel.CRITICAL,
    "high": ImpactLevel.HIGH,
    "medium": ImpactLevel.MEDIUM,
    "moderate": ImpactLevel.MEDIUM,
    "low": ImpactLevel.LOW,
    "info": ImpactLevel.NONE,
    "none": ImpactLevel.NONE,
}


@dataclass
class BlastNode:
    """A single node in the blast-radius graph.

    Attributes:
        node_id: Stable unique identifier.
        node_type: The :class:`NodeType` of this entity.
        name: Human-readable name (CVE id, package name, agent id, ...).
        metadata: Arbitrary structured metadata (version, ecosystem, scope).
        impact: The intrinsic impact level of this node.
    """

    node_id: str
    node_type: NodeType
    name: str
    metadata: dict[str, Any] = field(default_factory=dict)
    impact: ImpactLevel = ImpactLevel.NONE

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict for logging/API responses."""
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "name": self.name,
            "metadata": dict(self.metadata),
            "impact": self.impact.value,
        }


@dataclass
class BlastEdge:
    """A directed edge between two blast-radius nodes.

    Attributes:
        source_id: The source node id.
        target_id: The target node id.
        relationship: Human-readable relationship label (e.g. ``"affects"``).
        metadata: Optional structured metadata for the edge.
    """

    source_id: str
    target_id: str
    relationship: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict."""
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relationship": self.relationship,
            "metadata": dict(self.metadata),
        }


@dataclass
class BlastPath:
    """A complete path through the blast-radius graph.

    Attributes:
        nodes: Ordered list of nodes from source to target.
        edges: Ordered list of edges connecting the nodes.
        total_impact: The aggregate impact of the path (max of node impacts).
        description: Human-readable summary of the path.
    """

    nodes: list[BlastNode]
    edges: list[BlastEdge]
    total_impact: ImpactLevel
    description: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict."""
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "total_impact": self.total_impact.value,
            "description": self.description,
        }


class BlastRadiusError(AizeeError):
    """Raised when the blast-radius graph encounters an internal error."""

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        super().__init__("BLAST_RADIUS_ERROR", message, ErrorSeverity.HIGH, context)


# -- Module-level traversal helpers (kept outside the class to respect
#    the <300-line class-size rule [CODE-03]). -------------------------------

_TERMINAL_TYPES: frozenset[NodeType] = frozenset({NodeType.CREDENTIAL, NodeType.TOOL})


def _aggregate_impact(nodes: list[BlastNode]) -> ImpactLevel:
    """Return the highest impact level among the given nodes."""
    best = ImpactLevel.NONE
    for n in nodes:
        if _IMPACT_RANK[n.impact] > _IMPACT_RANK[best]:
            best = n.impact
    return best


def _build_path(nodes: list[BlastNode], edges: list[BlastEdge]) -> BlastPath:
    """Construct a BlastPath from collected nodes and edges."""
    names = " -> ".join(n.name for n in nodes)
    return BlastPath(
        nodes=nodes,
        edges=edges,
        total_impact=_aggregate_impact(nodes),
        description=f"Blast path: {names}",
    )


def _bfs_all_paths(
    nodes: dict[str, BlastNode],
    adjacency: dict[str, list[tuple[str, BlastEdge]]],
    start: str,
) -> list[BlastPath]:
    """BFS that collects all simple paths from *start* to terminal nodes."""
    paths: list[BlastPath] = []
    queue: deque[tuple[str, set[str], list[BlastNode], list[BlastEdge]]] = deque()
    queue.append((start, {start}, [nodes[start]], []))
    while queue:
        current_id, visited, path_nodes, path_edges = queue.popleft()
        current_node = nodes[current_id]
        if current_node.node_type in _TERMINAL_TYPES and len(path_nodes) > 1:
            paths.append(_build_path(path_nodes, path_edges))
        for target_id, edge in adjacency.get(current_id, []):
            if target_id in visited:
                continue
            queue.append(
                (
                    target_id,
                    visited | {target_id},
                    [*path_nodes, nodes[target_id]],
                    [*path_edges, edge],
                )
            )
    return paths


def _bfs_shortest(
    nodes: dict[str, BlastNode],
    adjacency: dict[str, list[tuple[str, BlastEdge]]],
    source: str,
    target_type: NodeType,
) -> BlastPath | None:
    """BFS returning the first path from *source* to a node of *target_type*."""
    visited: set[str] = {source}
    queue: deque[tuple[str, list[BlastNode], list[BlastEdge]]] = deque()
    queue.append((source, [nodes[source]], []))
    while queue:
        current_id, path_nodes, path_edges = queue.popleft()
        current_node = nodes[current_id]
        if current_node.node_type is target_type and len(path_nodes) > 1:
            return _build_path(path_nodes, path_edges)
        for target_id, edge in adjacency.get(current_id, []):
            if target_id in visited:
                continue
            visited.add(target_id)
            queue.append(
                (
                    target_id,
                    [*path_nodes, nodes[target_id]],
                    [*path_edges, edge],
                )
            )
    return None


def _reachable_nodes(
    adjacency: dict[str, list[tuple[str, BlastEdge]]],
    start: str,
) -> set[str]:
    """Return the set of node ids reachable from *start* (inclusive)."""
    visited: set[str] = set()
    queue: deque[str] = deque([start])
    while queue:
        current = queue.popleft()
        if current in visited:
            continue
        visited.add(current)
        for target_id, _ in adjacency.get(current, []):
            if target_id not in visited:
                queue.append(target_id)
    return visited


class BlastRadiusGraph:
    """Directed graph tracking AI supply-chain blast radius.

    Nodes represent entities (CVE, package, MCP server, agent, credential,
    tool, policy).  Edges represent dependency or exposure relationships.
    All public methods are thread-safe.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, BlastNode] = {}
        self._adjacency: dict[str, list[tuple[str, BlastEdge]]] = {}
        self._lock = threading.RLock()

    # -- node / edge management --------------------------------------------

    def add_node(self, node: BlastNode) -> None:
        """Add or replace a node in the graph.

        Raises:
            ValidationError: if *node* has an empty ``node_id``.
        """
        if not node.node_id:
            raise ValidationError("BlastNode.node_id must not be empty")
        with self._lock:
            self._nodes[node.node_id] = node
            self._adjacency.setdefault(node.node_id, [])
            _logger.debug(
                "Added blast-radius node",
                extra={"node_id": node.node_id, "node_type": node.node_type.value},
            )

    def add_edge(self, edge: BlastEdge) -> None:
        """Add a directed edge.  Both endpoints must already exist.

        Raises:
            ValidationError: if *source_id* or *target_id* is not a known node.
        """
        with self._lock:
            if edge.source_id not in self._nodes:
                raise ValidationError(f"Unknown source node: {edge.source_id!r}")
            if edge.target_id not in self._nodes:
                raise ValidationError(f"Unknown target node: {edge.target_id!r}")
            self._adjacency[edge.source_id].append((edge.target_id, edge))

    # -- convenience adders -------------------------------------------------

    def add_cve(self, cve_id: str, package_name: str, severity: str) -> BlastNode:
        """Create a CVE node linked to an (existing or new) package node.

        Args:
            cve_id: The CVE identifier (e.g. ``"CVE-2024-1234"``).
            package_name: The affected package name.
            severity: Severity string (``"critical"``, ``"high"``, ...).

        Returns:
            The created CVE :class:`BlastNode`.
        """
        impact = _SEVERITY_MAP.get(severity.lower(), ImpactLevel.MEDIUM)
        cve_node = BlastNode(
            node_id=f"cve:{cve_id}",
            node_type=NodeType.CVE,
            name=cve_id,
            metadata={"package": package_name, "severity": severity},
            impact=impact,
        )
        with self._lock:
            self.add_node(cve_node)
            pkg_node_id = f"pkg:{package_name}"
            if pkg_node_id not in self._nodes:
                self.add_package(package_name, "", "")
            self.add_edge(
                BlastEdge(
                    source_id=cve_node.node_id,
                    target_id=pkg_node_id,
                    relationship="affects",
                )
            )
        return cve_node

    def add_package(self, name: str, version: str, ecosystem: str) -> BlastNode:
        """Create (or replace) a package node."""
        node = BlastNode(
            node_id=f"pkg:{name}",
            node_type=NodeType.PACKAGE,
            name=name,
            metadata={"version": version, "ecosystem": ecosystem},
            impact=ImpactLevel.NONE,
        )
        self.add_node(node)
        return node

    def add_mcp_server(self, name: str, packages: list[str]) -> BlastNode:
        """Create an MCP-server node and link it to the given packages."""
        node = BlastNode(
            node_id=f"mcp:{name}",
            node_type=NodeType.MCP_SERVER,
            name=name,
            metadata={"packages": list(packages)},
            impact=ImpactLevel.NONE,
        )
        with self._lock:
            self.add_node(node)
            for pkg in packages:
                pkg_id = f"pkg:{pkg}"
                if pkg_id not in self._nodes:
                    self.add_package(pkg, "", "")
                self.add_edge(
                    BlastEdge(
                        source_id=pkg_id,
                        target_id=node.node_id,
                        relationship="used_by",
                    )
                )
        return node

    def add_agent(
        self,
        agent_id: str,
        mcp_servers: list[str],
        credentials: list[str],
    ) -> BlastNode:
        """Create an agent node linked to MCP servers and credentials."""
        node = BlastNode(
            node_id=f"agent:{agent_id}",
            node_type=NodeType.AGENT,
            name=agent_id,
            metadata={"mcp_servers": list(mcp_servers), "credentials": list(credentials)},
            impact=ImpactLevel.NONE,
        )
        with self._lock:
            self.add_node(node)
            for srv in mcp_servers:
                srv_id = f"mcp:{srv}"
                if srv_id in self._nodes:
                    self.add_edge(
                        BlastEdge(
                            source_id=srv_id,
                            target_id=node.node_id,
                            relationship="exposes",
                        )
                    )
            for cred in credentials:
                cred_id = f"cred:{cred}"
                if cred_id not in self._nodes:
                    self.add_credential(cred, "", "")
                self.add_edge(
                    BlastEdge(
                        source_id=node.node_id,
                        target_id=cred_id,
                        relationship="holds",
                    )
                )
        return node

    def add_credential(self, cred_id: str, cred_type: str, scope: str) -> BlastNode:
        """Create a credential node."""
        node = BlastNode(
            node_id=f"cred:{cred_id}",
            node_type=NodeType.CREDENTIAL,
            name=cred_id,
            metadata={"type": cred_type, "scope": scope},
            impact=ImpactLevel.HIGH,
        )
        self.add_node(node)
        return node

    def add_tool(self, tool_name: str, agent_id: str) -> BlastNode:
        """Create a tool node linked to an agent."""
        node = BlastNode(
            node_id=f"tool:{tool_name}",
            node_type=NodeType.TOOL,
            name=tool_name,
            metadata={"agent": agent_id},
            impact=ImpactLevel.NONE,
        )
        with self._lock:
            self.add_node(node)
            agent_id_full = f"agent:{agent_id}"
            if agent_id_full in self._nodes:
                self.add_edge(
                    BlastEdge(
                        source_id=agent_id_full,
                        target_id=node.node_id,
                        relationship="invokes",
                    )
                )
        return node

    # -- traversal ----------------------------------------------------------

    def trace(self, start_node_id: str) -> list[BlastPath]:
        """Find all paths from *start_node_id* to credential/tool nodes.

        Uses BFS to enumerate simple paths (no repeated nodes).  Returns an
        empty list if the start node does not exist or no paths are found.
        """
        with self._lock:
            if start_node_id not in self._nodes:
                return []
            return _bfs_all_paths(self._nodes, self._adjacency, start_node_id)

    def impact(self, node_id: str) -> ImpactLevel:
        """Compute the blast-radius impact for *node_id*.

        The impact is the highest impact level reachable from *node_id*
        through any path in the graph (including the node itself).
        Returns :attr:`ImpactLevel.NONE` if the node does not exist.
        """
        with self._lock:
            if node_id not in self._nodes:
                return ImpactLevel.NONE
            reachable = _reachable_nodes(self._adjacency, node_id)
            return _aggregate_impact([self._nodes[n] for n in reachable])

    def shortest_path(
        self,
        source_id: str,
        target_type: NodeType,
    ) -> BlastPath | None:
        """Find the shortest path from *source_id* to any node of *target_type*.

        Returns ``None`` if no such path exists or the source node is unknown.
        """
        with self._lock:
            if source_id not in self._nodes:
                return None
            return _bfs_shortest(self._nodes, self._adjacency, source_id, target_type)

    # -- serialization / stats ---------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize the entire graph to a plain dict."""
        with self._lock:
            all_edges: list[BlastEdge] = []
            for edges in self._adjacency.values():
                all_edges.extend(e for _, e in edges)
            return {
                "nodes": [n.to_dict() for n in self._nodes.values()],
                "edges": [e.to_dict() for e in all_edges],
            }

    def stats(self) -> dict[str, int]:
        """Return node and edge counts broken down by type."""
        with self._lock:
            node_counts: dict[str, int] = {t.value: 0 for t in NodeType}
            for n in self._nodes.values():
                node_counts[n.node_type.value] += 1
            edge_count = sum(len(v) for v in self._adjacency.values())
            result: dict[str, int] = {
                "total_nodes": len(self._nodes),
                "total_edges": edge_count,
            }
            result.update({f"nodes_{k}": v for k, v in node_counts.items()})
            return result
