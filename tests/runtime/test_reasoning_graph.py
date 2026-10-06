"""Tests for runtime/reasoning_graph.py."""

from __future__ import annotations

import pytest

from runtime.reasoning_graph import NodeKind, ReasoningGraph


class TestReasoningGraph:
    def test_add_node(self):
        g = ReasoningGraph()
        n = g.add_node("a", kind=NodeKind.FINDING, description="test")
        assert n.id == "a"
        assert "a" in g.nodes

    def test_add_edge_requires_nodes(self):
        g = ReasoningGraph()
        with pytest.raises(KeyError):
            g.add_edge("a", "b")

    def test_activate(self):
        g = ReasoningGraph()
        g.add_node("a")
        g.activate("a")
        assert g.nodes["a"].activated is True

    def test_activate_unknown(self):
        g = ReasoningGraph()
        with pytest.raises(KeyError):
            g.activate("nope")

    def test_propagate(self):
        g = ReasoningGraph()
        g.add_node("finding", NodeKind.FINDING)
        g.add_node("escalate", NodeKind.ESCALATION)
        g.add_node("remediate", NodeKind.ACTION)
        g.add_node("verify", NodeKind.CHECK)
        g.add_edge("finding", "escalate")
        g.add_edge("escalate", "remediate")
        g.add_edge("remediate", "verify")
        g.activate("finding")
        newly = g.propagate()
        assert set(newly) == {"escalate", "remediate", "verify"}
        assert all(g.nodes[n].activated for n in ["finding", "escalate", "remediate", "verify"])

    def test_active_path(self):
        g = ReasoningGraph()
        for nid in ["a", "b", "c", "d"]:
            g.add_node(nid)
        g.add_edge("a", "b")
        g.add_edge("b", "c")
        g.add_edge("c", "d")
        g.activate("a")
        g.propagate()
        assert g.active_path() == ["a", "b", "c", "d"]

    def test_active_path_empty(self):
        g = ReasoningGraph()
        g.add_node("a")
        assert g.active_path() == []

    def test_reset(self):
        g = ReasoningGraph()
        g.add_node("a")
        g.add_node("b")
        g.add_edge("a", "b")
        g.activate("a")
        g.propagate()
        g.reset()
        assert g.active_nodes() == []

    def test_stats(self):
        g = ReasoningGraph()
        g.add_node("a")
        g.add_node("b")
        g.add_edge("a", "b")
        g.activate("a")
        g.propagate()
        s = g.stats()
        assert s["nodes"] == 2
        assert s["edges"] == 1
        assert s["activated"] == 2

    def test_branching_path_picks_longest(self):
        g = ReasoningGraph()
        for nid in ["root", "short", "long1", "long2"]:
            g.add_node(nid)
        g.add_edge("root", "short")
        g.add_edge("root", "long1")
        g.add_edge("long1", "long2")
        g.activate("root")
        g.propagate()
        path = g.active_path()
        assert path == ["root", "long1", "long2"]

    def test_edges_property(self):
        g = ReasoningGraph()
        g.add_node("a")
        g.add_node("b")
        e = g.add_edge("a", "b", condition="x>0")
        assert e in g.edges
        assert e.condition == "x>0"
