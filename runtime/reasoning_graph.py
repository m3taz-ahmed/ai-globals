#!/usr/bin/env python3
"""Reasoning graph for multi-step governance escalation chains.

Inspired by Omnigent's ``reasoning_graph.py``: a directed graph where
nodes represent capabilities/states and edges represent reasoning steps.
When a finding is confirmed, downstream edges activate, letting the
agent follow multi-step escalation paths (e.g. policy_violation →
escalate → remediate → verify).

For aiZee, this models governance chains: a policy violation can trigger
escalation, which triggers remediation, which triggers verification.
The graph is deterministic and side-effect-free — it computes which
paths are active; the caller decides what to do with them.

Usage::

    from runtime.reasoning_graph import ReasoningGraph, Node, Edge
    g = ReasoningGraph()
    g.add_node("policy_violation", kind="finding")
    g.add_node("escalate", kind="action")
    g.add_node("remediate", kind="action")
    g.add_node("verify", kind="check")
    g.add_edge("policy_violation", "escalate")
    g.add_edge("escalate", "remediate")
    g.add_edge("remediate", "verify")
    g.activate("policy_violation")
    path = g.active_path()  # ["policy_violation", "escalate", "remediate", "verify"]
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class NodeKind(str, Enum):
    """Kind of a reasoning node."""

    FINDING = "finding"        # an observed condition
    ACTION = "action"          # a step to take
    CHECK = "check"            # a verification step
    ESCALATION = "escalation"  # an escalation point
    TERMINAL = "terminal"      # end state (resolved/failed)


@dataclass
class Node:
    """A node in the reasoning graph."""

    id: str
    kind: NodeKind = NodeKind.ACTION
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    activated: bool = False


@dataclass
class Edge:
    """A directed edge between two nodes."""

    source: str
    target: str
    condition: str = ""  # optional description of when this edge fires
    weight: float = 1.0


class ReasoningGraph:
    """Directed graph for multi-step reasoning chains.

    Nodes are activated manually (``activate``) or automatically when a
    predecessor is activated (``propagate``). The active path is the
    longest chain of activated nodes from any root.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, Node] = {}
        self._out: dict[str, list[Edge]] = defaultdict(list)
        self._in: dict[str, list[Edge]] = defaultdict(list)

    def add_node(
        self,
        node_id: str,
        kind: NodeKind = NodeKind.ACTION,
        description: str = "",
        **metadata: Any,
    ) -> Node:
        """Add a node. Overwrites if exists."""
        node = Node(id=node_id, kind=kind, description=description, metadata=metadata)
        self._nodes[node_id] = node
        return node

    def add_edge(
        self,
        source: str,
        target: str,
        condition: str = "",
        weight: float = 1.0,
    ) -> Edge:
        """Add a directed edge. Both nodes must exist."""
        if source not in self._nodes:
            raise KeyError(f"unknown source node {source!r}")
        if target not in self._nodes:
            raise KeyError(f"unknown target node {target!r}")
        edge = Edge(source=source, target=target, condition=condition, weight=weight)
        self._out[source].append(edge)
        self._in[target].append(edge)
        return edge

    def activate(self, node_id: str) -> None:
        """Activate a node (mark a finding as confirmed)."""
        if node_id not in self._nodes:
            raise KeyError(f"unknown node {node_id!r}")
        self._nodes[node_id].activated = True

    def propagate(self) -> list[str]:
        """Propagate activation downstream. Returns newly activated node ids.

        A node becomes activated if any of its predecessors is activated.
        This runs to fixpoint (BFS).
        """
        newly: list[str] = []
        queue: deque[str] = deque()
        for nid, node in self._nodes.items():
            if node.activated:
                queue.append(nid)
        while queue:
            current = queue.popleft()
            for edge in self._out[current]:
                target = self._nodes[edge.target]
                if not target.activated:
                    target.activated = True
                    newly.append(edge.target)
                    queue.append(edge.target)
        return newly

    def active_path(self) -> list[str]:
        """Return the longest chain of activated nodes from any root.

        Roots are activated nodes with no activated predecessors.
        """
        activated = [nid for nid, n in self._nodes.items() if n.activated]
        if not activated:
            return []
        # Find roots: activated nodes with no activated incoming edges.
        roots = [
            nid for nid in activated
            if not any(
                self._nodes[e.source].activated for e in self._in[nid]
            )
        ]
        # BFS longest path from each root.
        best: list[str] = []
        for root in roots:
            path = self._longest_path(root)
            if len(path) > len(best):
                best = path
        return best

    def _longest_path(self, start: str) -> list[str]:
        """Longest simple path from start through activated nodes."""
        best = [start]
        for edge in self._out[start]:
            if self._nodes[edge.target].activated:
                sub = self._longest_path(edge.target)
                if len(sub) + 1 > len(best):
                    best = [start, *sub]
        return best

    def reset(self) -> None:
        """Deactivate all nodes."""
        for node in self._nodes.values():
            node.activated = False

    @property
    def nodes(self) -> dict[str, Node]:
        return dict(self._nodes)

    @property
    def edges(self) -> list[Edge]:
        return [e for edges in self._out.values() for e in edges]

    def active_nodes(self) -> list[Node]:
        return [n for n in self._nodes.values() if n.activated]

    def stats(self) -> dict[str, int]:
        return {
            "nodes": len(self._nodes),
            "edges": len(self.edges),
            "activated": len(self.active_nodes()),
        }
