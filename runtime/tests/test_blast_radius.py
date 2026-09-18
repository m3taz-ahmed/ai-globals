"""Tests for runtime/blast_radius.py — AI supply-chain blast radius graph."""

from __future__ import annotations

import pytest

from runtime.blast_radius import (
    BlastEdge,
    BlastNode,
    BlastRadiusError,
    BlastRadiusGraph,
    ImpactLevel,
    NodeType,
)
from runtime.schemas import ValidationError


def _full_graph() -> tuple[BlastRadiusGraph, BlastNode]:
    """CVE -> package -> MCP server -> agent -> credential + tool."""
    g = BlastRadiusGraph()
    cve = g.add_cve("CVE-2024-1", "evil-pkg", "critical")
    g.add_mcp_server("srv", ["evil-pkg"])
    g.add_agent("agent1", ["srv"], ["apikey"])
    g.add_tool("send_email", "agent1")
    return g, cve


class TestNodeEdgeManagement:
    def test_add_node_empty_id(self):
        g = BlastRadiusGraph()
        with pytest.raises(ValidationError):
            g.add_node(BlastNode(node_id="", node_type=NodeType.TOOL, name="x"))

    def test_add_edge_unknown_source(self):
        g = BlastRadiusGraph()
        g.add_package("p", "1.0", "pypi")
        with pytest.raises(ValidationError, match="Unknown source"):
            g.add_edge(BlastEdge("nope", "pkg:p", "x"))

    def test_add_edge_unknown_target(self):
        g = BlastRadiusGraph()
        g.add_package("p", "1.0", "pypi")
        with pytest.raises(ValidationError, match="Unknown target"):
            g.add_edge(BlastEdge("pkg:p", "nope", "x"))

    def test_add_edge_ok(self):
        g = BlastRadiusGraph()
        g.add_package("a", "", "")
        g.add_package("b", "", "")
        g.add_edge(BlastEdge("pkg:a", "pkg:b", "depends"))
        assert g.stats()["total_edges"] == 1

    def test_node_replace(self):
        g = BlastRadiusGraph()
        g.add_package("p", "1.0", "pypi")
        g.add_package("p", "2.0", "pypi")
        assert g.stats()["total_nodes"] == 1


class TestConvenienceAdders:
    def test_add_cve_wires_package(self):
        g = BlastRadiusGraph()
        cve = g.add_cve("CVE-1", "pkg", "high")
        assert cve.node_id == "cve:CVE-1"
        assert cve.impact == ImpactLevel.HIGH
        assert cve.metadata["package"] == "pkg"
        # auto-created pkg node + affects edge
        assert "pkg:pkg" in g.to_dict()["nodes"][1]["node_id"]

    def test_cve_severity_map(self):
        g = BlastRadiusGraph()
        assert g.add_cve("C1", "p1", "moderate").impact == ImpactLevel.MEDIUM
        assert g.add_cve("C2", "p2", "unknown").impact == ImpactLevel.MEDIUM
        assert g.add_cve("C3", "p3", "info").impact == ImpactLevel.NONE

    def test_add_cve_existing_package(self):
        g = BlastRadiusGraph()
        g.add_package("pkg", "1.0", "pypi")
        g.add_cve("CVE-2", "pkg", "low")
        assert g.stats()["nodes_package"] == 1  # no duplicate

    def test_add_mcp_server(self):
        g = BlastRadiusGraph()
        srv = g.add_mcp_server("s", ["dep1", "dep2"])
        assert srv.node_type == NodeType.MCP_SERVER
        assert g.stats()["nodes_package"] == 2
        assert g.stats()["total_edges"] == 2

    def test_add_agent(self):
        g = BlastRadiusGraph()
        g.add_mcp_server("s", [])
        agent = g.add_agent("a1", ["s"], ["cred1"])
        assert agent.node_type == NodeType.AGENT
        assert g.stats()["nodes_credential"] == 1
        # s->agent (exposes) + agent->cred1 (holds)
        assert g.stats()["total_edges"] == 2

    def test_add_agent_skips_unknown_server(self):
        g = BlastRadiusGraph()
        g.add_agent("a1", ["nonexistent"], [])
        assert g.stats()["total_edges"] == 0

    def test_add_credential_high_impact(self):
        g = BlastRadiusGraph()
        c = g.add_credential("k", "api_key", "write")
        assert c.impact == ImpactLevel.HIGH
        assert c.metadata["scope"] == "write"

    def test_add_tool(self):
        g = BlastRadiusGraph()
        g.add_agent("a", [], [])
        g.add_tool("t1", "a")
        assert g.stats()["nodes_tool"] == 1
        assert g.stats()["total_edges"] == 1

    def test_add_tool_unknown_agent_no_edge(self):
        g = BlastRadiusGraph()
        g.add_tool("t1", "ghost")
        assert g.stats()["total_edges"] == 0


class TestTraversal:
    def test_trace_finds_terminal_paths(self):
        g, cve = _full_graph()
        paths = g.trace(cve.node_id)
        assert len(paths) == 2  # -> credential + -> tool
        names = {p.nodes[-1].node_type for p in paths}
        assert names == {NodeType.CREDENTIAL, NodeType.TOOL}
        for p in paths:
            assert p.nodes[0].node_id == cve.node_id
            assert p.total_impact in (ImpactLevel.HIGH, ImpactLevel.CRITICAL)
            assert "Blast path:" in p.description

    def test_trace_unknown_start(self):
        assert BlastRadiusGraph().trace("nope") == []

    def test_trace_no_terminal(self):
        g = BlastRadiusGraph()
        g.add_package("a", "", "")
        g.add_package("b", "", "")
        g.add_edge(BlastEdge("pkg:a", "pkg:b", "x"))
        assert g.trace("pkg:a") == []

    def test_cycle_terminates(self):
        g = BlastRadiusGraph()
        g.add_package("a", "", "")
        g.add_package("b", "", "")
        g.add_edge(BlastEdge("pkg:a", "pkg:b", "x"))
        g.add_edge(BlastEdge("pkg:b", "pkg:a", "x"))
        assert g.trace("pkg:a") == []

    def test_impact_aggregates_reachable(self):
        g, cve = _full_graph()
        assert g.impact(cve.node_id) == ImpactLevel.CRITICAL  # cve itself critical
        pkg_impact = g.impact("pkg:evil-pkg")
        assert pkg_impact == ImpactLevel.HIGH  # reaches HIGH credential

    def test_impact_unknown(self):
        assert BlastRadiusGraph().impact("ghost") == ImpactLevel.NONE

    def test_impact_isolated(self):
        g = BlastRadiusGraph()
        g.add_package("iso", "", "")
        assert g.impact("pkg:iso") == ImpactLevel.NONE

    def test_shortest_path(self):
        g, cve = _full_graph()
        p = g.shortest_path(cve.node_id, NodeType.CREDENTIAL)
        assert p is not None
        assert p.nodes[-1].node_type == NodeType.CREDENTIAL
        assert p.nodes[0].node_id == cve.node_id

    def test_shortest_path_none(self):
        g = BlastRadiusGraph()
        g.add_package("a", "", "")
        assert g.shortest_path("pkg:a", NodeType.CREDENTIAL) is None

    def test_shortest_path_unknown_source(self):
        assert BlastRadiusGraph().shortest_path("x", NodeType.TOOL) is None


class TestSerialization:
    def test_to_dict(self):
        g, _ = _full_graph()
        d = g.to_dict()
        assert len(d["nodes"]) == 6  # cve, pkg, mcp, agent, cred, tool
        types = {n["node_type"] for n in d["nodes"]}
        assert NodeType.CVE.value in types and NodeType.CREDENTIAL.value in types
        assert all("source_id" in e for e in d["edges"])

    def test_stats(self):
        g, _ = _full_graph()
        s = g.stats()
        assert s["nodes_cve"] == 1
        assert s["nodes_agent"] == 1
        assert s["total_edges"] >= 3
        assert s["total_nodes"] == s["nodes_cve"] + s["nodes_package"] + \
            s["nodes_mcp_server"] + s["nodes_agent"] + s["nodes_credential"] + \
            s["nodes_tool"] + s["nodes_policy"]

    def test_path_to_dict(self):
        g, cve = _full_graph()
        p = g.trace(cve.node_id)[0].to_dict()
        assert p["total_impact"] in ("high", "critical")
        assert len(p["nodes"]) == len(p["edges"]) + 1

    def test_blast_error(self):
        err = BlastRadiusError("boom", {"k": 1})
        assert err.error_code == "BLAST_RADIUS_ERROR"
        assert err.context == {"k": 1}
