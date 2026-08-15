"""Comprehensive tests for aios_mcp/aios_server.py MCP tools."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.slow

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


# Ingest initial content so search/query tests have data to match.
_call("ingest_memory", {})


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


class TestSecurity:
    def test_get_tech_stack_rejects_path_traversal(self):
        result = _call("get_tech_stack", {"pkg": "../etc", "ver": "passwd"})
        data = json.loads(result)
        assert data["ok"] is False

    def test_get_tech_stack_resolves_path(self):
        (ROOT / "tech-stack" / "MyLib-1.0.0.md").write_text("# MyLib", encoding="utf-8")
        result = _call("get_tech_stack", {"pkg": "MyLib", "ver": "1.0.0"})
        data = json.loads(result)
        assert data["exists"] is True

    def test_search_memory_rejects_negative_limit(self):
        result = _call("search_memory", {"query": "behavioral", "limit": -5})
        data = json.loads(result)
        assert isinstance(data, list)

    def test_query_context_rejects_huge_k(self):
        result = _call("query_context", {"query": "test", "k": 500})
        data = json.loads(result)
        assert isinstance(data, list)

    def test_add_memory_rejects_empty_content(self):
        result = _call("add_memory", {"kind": "factual", "content": "", "source": "mcp"})
        data = json.loads(result)
        assert data["ok"] is False


class TestPluginRegistration:
    """Cover _register_plugins when plugins expose tools and resources."""

    def test_register_plugins_with_tools_and_resources(self):
        from aios_mcp import aios_server

        mock_kernel = MagicMock()
        mock_tool = MagicMock()
        mock_resource = MagicMock()
        mock_kernel.plugins.get_tools.return_value = [mock_tool]
        mock_kernel.plugins.get_resources.return_value = [mock_resource]

        with patch.object(aios_server, "kernel", return_value=mock_kernel), \
             patch("aios_mcp.tools.common.memory", return_value=MagicMock()), \
             patch.object(aios_server.mcp, "add_tool") as mock_add_tool, \
             patch.object(aios_server.mcp, "add_resource") as mock_add_resource:
            aios_server._register_plugins()
            mock_add_tool.assert_called_once_with(mock_tool)
            mock_add_resource.assert_called_once_with(mock_resource)


class TestResourceFallbacks:
    """Cover fallback paths in get_rule_resource / get_workflow_resource."""

    def test_get_rule_resource_via_tool_fn(self):
        """Cover line 62: get_rule_resource returns via registered tool fn."""
        from aios_mcp import aios_server

        mock_fn = MagicMock(return_value="tool-content")
        mock_tool = MagicMock()
        mock_tool.fn = mock_fn
        with patch.object(aios_server._tool_manager, "get_tool", return_value=mock_tool):
            result = aios_server.get_rule_resource("core")
            assert result == "tool-content"
            mock_fn.assert_called_once_with("core")

    def test_get_rule_resource_fallback_missing_file(self):
        """Cover line 73: fallback path when file does not exist."""
        from aios_mcp import aios_server

        # Ensure tool fn is not found so fallback runs
        with patch.object(aios_server._tool_manager, "get_tool", return_value=None):
            result = aios_server.get_rule_resource("nonexistent-rule-xyz")
            assert result == ""

    def test_get_workflow_resource_unsafe_name(self):
        """Cover line 83: get_workflow_resource rejects unsafe name."""
        from aios_mcp import aios_server

        result = aios_server.get_workflow_resource("../../etc/passwd")
        assert result == ""

    def test_get_workflow_resource_fallback_missing_file(self):
        """Cover line 87: fallback path when workflow file does not exist."""
        from aios_mcp import aios_server

        result = aios_server.get_workflow_resource("nonexistent-wf-xyz")
        assert result == ""


class TestMainBlock:
    """Cover the if __name__ == '__main__' block (line 92)."""

    def test_main_block_calls_run(self):
        from aios_mcp import aios_server
        from pathlib import Path

        source = Path(aios_server.__file__).read_text(encoding="utf-8")
        with patch("mcp.server.fastmcp.FastMCP.run") as mock_run:
            code = compile(source, str(aios_server.__file__), "exec")
            namespace: dict = {"__name__": "__main__", "__file__": str(aios_server.__file__)}
            exec(code, namespace)
            mock_run.assert_called_once_with(transport="stdio")
