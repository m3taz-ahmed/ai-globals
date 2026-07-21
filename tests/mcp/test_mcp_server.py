"""Comprehensive tests for aios_mcp/aios_server.py MCP tools."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

# Set up isolated root BEFORE importing the server module
os.environ["AGENT_OS_ROOT"] = tempfile.mkdtemp(prefix="aios_mcp_test_")
ROOT = Path(os.environ["AGENT_OS_ROOT"])
for sub in ("runtime/policies", "workflows", "rules", "tech-stack", "state", "brain"):
    (ROOT / sub).mkdir(parents=True, exist_ok=True)
(ROOT / "runtime/policies/default.yaml").write_text(
    "default_action: ask\nrules:\n"
    "  - name: allow-read\n    condition: \"type == 'Read'\"\n    action: allow\n"
)
(ROOT / "workflows/test.md").write_text(
    "[WORKFLOW] test\n[OBJ] Test workflow for MCP tests.\n[RULES]\n1. [REQ] Step one.\n"
)
(ROOT / "rules/core.md").write_text(
    "# Core rules\nThis covers behavioral rules for agents."
)

from aios_mcp.aios_server import mcp  # noqa: E402


def _call(name: str, arguments: dict) -> str:
    from aios_mcp import aios_server

    os.environ["AGENT_OS_ROOT"] = str(ROOT)
    aios_server.reset_state()
    return mcp._tool_manager.get_tool(name).fn(**arguments)


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------

class TestToolsList:
    def test_all_expected_tools_registered(self):
        tools = mcp._tool_manager._tools.values()
        names = {t.name for t in tools}
        expected = {
            "check_policy",
            "search_memory",
            "search_memory_vector",
            "query_context",
            "ingest_memory",
            "get_related_memories",
            "get_tech_stack",
            "list_rules",
            "get_rule",
            "list_workflows",
            "get_workflow",
            "run_workflow",
            "query_rules",
        }
        assert expected.issubset(names), f"Missing tools: {expected - names}"


# ---------------------------------------------------------------------------
# check_policy
# ---------------------------------------------------------------------------

class TestCheckPolicy:
    def test_read_allowed(self):
        result = _call("check_policy", {"action": "Read"})
        data = json.loads(result)
        assert data["ok"] is True

    def test_check_with_args(self):
        result = _call("check_policy", {"action": "Read", "args": {"user": "alice"}})
        data = json.loads(result)
        assert data["ok"] is True


# ---------------------------------------------------------------------------
# search_memory
# ---------------------------------------------------------------------------

class TestSearchMemory:
    def test_search_memory_empty_result(self):
        result = _call("search_memory", {"query": "nonexistent_xyz_987"})
        data = json.loads(result)
        assert isinstance(data, list)

    def test_search_memory_with_kind(self):
        result = _call("search_memory", {"query": "rules", "kind": "semantic"})
        data = json.loads(result)
        assert isinstance(data, list)

    def test_search_memory_result_has_source(self):
        result = _call("search_memory", {"query": "behavioral rules"})
        data = json.loads(result)
        if data:
            assert "source" in data[0]
            assert "kind" in data[0]
            assert "content" in data[0]


# ---------------------------------------------------------------------------
# search_memory_vector
# ---------------------------------------------------------------------------

class TestSearchMemoryVector:
    def test_search_memory_vector_returns_list(self):
        result = _call("search_memory_vector", {"query": "rules", "k": 3})
        data = json.loads(result)
        assert isinstance(data, list)

    def test_search_memory_vector_with_kind(self):
        result = _call("search_memory_vector", {"query": "rules", "k": 3, "kind": "semantic"})
        data = json.loads(result)
        assert isinstance(data, list)


# ---------------------------------------------------------------------------
# query_context (hybrid FTS + vector)
# ---------------------------------------------------------------------------

class TestQueryContext:
    def test_query_context_returns_list(self):
        result = _call("query_context", {"query": "behavioral rules"})
        data = json.loads(result)
        assert isinstance(data, list)

    def test_query_context_with_kind(self):
        result = _call("query_context", {"query": "rules", "k": 3, "kind": "semantic"})
        data = json.loads(result)
        assert isinstance(data, list)

    def test_query_context_result_structure(self):
        result = _call("query_context", {"query": "behavioral"})
        data = json.loads(result)
        if data:
            item = data[0]
            assert "id" in item
            assert "kind" in item
            assert "source" in item
            assert "content" in item
            assert "fts" in item


# ---------------------------------------------------------------------------
# ingest_memory
# ---------------------------------------------------------------------------

class TestIngestMemory:
    def test_ingest_memory_returns_count(self):
        # Add a rule file to ingest
        (ROOT / "rules" / "new-rule.md").write_text("# New Rule\nContent here.")
        result = _call("ingest_memory", {})
        data = json.loads(result)
        assert "ingested" in data
        assert isinstance(data["ingested"], int)

    def test_ingest_memory_second_call_is_idempotent(self):
        result1 = _call("ingest_memory", {})
        result2 = _call("ingest_memory", {})
        d1 = json.loads(result1)
        d2 = json.loads(result2)
        # Second call should ingest 0 (nothing changed)
        assert d2["ingested"] == 0


# ---------------------------------------------------------------------------
# get_related_memories
# ---------------------------------------------------------------------------

class TestGetRelatedMemories:
    def test_get_related_no_relations(self):
        result = _call("get_related_memories", {"mem_id": "00000000-0000-0000-0000-000000000000"})
        data = json.loads(result)
        assert data == []


# ---------------------------------------------------------------------------
# get_tech_stack
# ---------------------------------------------------------------------------

class TestGetTechStack:
    def test_missing_package(self):
        result = _call("get_tech_stack", {"pkg": "nonexistent", "ver": "1.0"})
        data = json.loads(result)
        assert data["exists"] is False

    def test_invalid_package_name(self):
        result = _call("get_tech_stack", {"pkg": "../etc/passwd", "ver": "1.0"})
        data = json.loads(result)
        assert data["ok"] is False

    def test_existing_package(self):
        (ROOT / "tech-stack" / "mylib-2.0.md").write_text("# MyLib 2.0\nDocs here.")
        result = _call("get_tech_stack", {"pkg": "mylib", "ver": "2.0"})
        data = json.loads(result)
        assert data["exists"] is True
        assert "MyLib" in data["content"]


# ---------------------------------------------------------------------------
# list_rules / get_rule
# ---------------------------------------------------------------------------

class TestRules:
    def test_list_rules_returns_list(self):
        result = _call("list_rules", {})
        data = json.loads(result)
        assert isinstance(data, list)
        assert any(r["id"] == "core" for r in data)

    def test_get_rule_existing(self):
        result = _call("get_rule", {"id": "core"})
        data = json.loads(result)
        assert data["exists"] is True
        assert "Core rules" in data["content"]

    def test_get_rule_missing(self):
        result = _call("get_rule", {"id": "nonexistent-rule"})
        data = json.loads(result)
        assert data["exists"] is False

    def test_get_rule_invalid_id(self):
        result = _call("get_rule", {"id": "../../../etc/passwd"})
        data = json.loads(result)
        assert data["ok"] is False

    def test_query_rules_match(self):
        result = _call("query_rules", {"query": "behavioral"})
        data = json.loads(result)
        assert isinstance(data, list)
        assert len(data) >= 1


# ---------------------------------------------------------------------------
# list_workflows / get_workflow
# ---------------------------------------------------------------------------

class TestWorkflows:
    def test_list_workflows_returns_list(self):
        result = _call("list_workflows", {})
        data = json.loads(result)
        assert isinstance(data, list)
        assert any(w["id"] == "test" for w in data)

    def test_get_workflow_existing(self):
        result = _call("get_workflow", {"id": "test"})
        data = json.loads(result)
        assert data["exists"] is True

    def test_get_workflow_missing(self):
        result = _call("get_workflow", {"id": "nonexistent"})
        data = json.loads(result)
        assert data["exists"] is False

    def test_get_workflow_invalid_id(self):
        result = _call("get_workflow", {"id": "../../secret"})
        data = json.loads(result)
        assert data["ok"] is False


class TestExtensions:
    def test_analyze_budget(self):
        result = _call("analyze_budget", {})
        data = json.loads(result)
        assert "usage" in data
        assert "budgets" in data

    def test_add_and_invalidate_memory(self):
        result = _call("add_memory", {"kind": "factual", "content": "test new mcp memory", "source": "mcp"})
        data = json.loads(result)
        assert data["ok"] is True
        mem_id = data["id"]
        
        result2 = _call("invalidate_memory", {"id": mem_id})
        data2 = json.loads(result2)
        assert data2["ok"] is True
        assert data2["id"] == mem_id
        
        result3 = _call("invalidate_memory", {"id": "nonexistent"})
        data3 = json.loads(result3)
        assert data3["ok"] is False

    def test_resources_direct_call(self):
        from aios_mcp.aios_server import get_rule_resource, get_workflow_resource
        core_rule = get_rule_resource("core")
        assert "Core rules" in core_rule
        
        bad_rule = get_rule_resource("../../etc/passwd")
        assert bad_rule == ""
        
        test_wf = get_workflow_resource("test")
        assert "[WORKFLOW] test" in test_wf
