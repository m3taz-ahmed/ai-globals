"""Tests for aizee_mcp/tools/workflow_tools.py — workflow, rules, and MCP plan tools."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from mcp.server.fastmcp import FastMCP

# Set up isolated root BEFORE importing
_ROOT = tempfile.mkdtemp(prefix="aios_wf_test_")
os.environ["AIZEE_ROOT"] = _ROOT
ROOT = Path(_ROOT)
for sub in ("rules", "workflows", "tech-stack", "skills", "state", "brain"):
    (ROOT / sub).mkdir(parents=True, exist_ok=True)

# Create rule files
(ROOT / "rules" / "core.md").write_text(
    "# Core Rules\nThis covers behavioral rules for agents.\n", encoding="utf-8"
)
(ROOT / "rules" / "scoped.md").write_text(
    "---\npaths:\n  - /special/project\n---\n# Scoped Rules\n"
    "These rules have a path scope. keyword: testing.\n",
    encoding="utf-8",
)
(ROOT / "rules" / "always.md").write_text(
    "---\nalways: true\n---\n# Always Rules\nThese always apply. keyword: testing.\n",
    encoding="utf-8",
)
# Create workflow files
(ROOT / "workflows" / "deploy.md").write_text(
    "[WORKFLOW] deploy\n[OBJ] Deploy workflow.\n[RULES]\n1. [REQ] Deploy step.\n",
    encoding="utf-8",
)

from aizee_mcp.tools.common import reset_state  # noqa: E402
from aizee_mcp.tools.workflow_tools import register_workflow_tools  # noqa: E402

_mcp = FastMCP("test-workflow")
register_workflow_tools(_mcp)


def _call(name: str, arguments: dict) -> str:
    os.environ["AIZEE_ROOT"] = _ROOT
    reset_state()
    return _mcp._tool_manager.get_tool(name).fn(**arguments)


def _get_resource_fn(uri_contains: str):
    """Get a resource template function by matching URI pattern."""
    templates = _mcp._resource_manager._templates
    for key, tmpl in templates.items():
        if uri_contains in str(key):
            return tmpl.fn
    return None  # pragma: no cover

class TestQueryRules:
    def test_invalid_query(self):
        """Cover line 38: validate_query error."""
        result = _call("query_rules", {"query": ""})
        data = json.loads(result)
        assert data["ok"] is False

    def test_get_resource_fn_no_match_returns_none(self):
        """Cover line 60: _get_resource_fn returns None when no template matches."""
        assert _get_resource_fn("nonexistent-pattern-xyz") is None

    def test_invalid_context_type(self):
        """Cover line 40: non-dict context rejected."""
        result = _call("query_rules", {"query": "test", "context": "not-a-dict"})
        data = json.loads(result)
        assert data["ok"] is False
        assert "Invalid context" in data["error"]

    def test_query_matches_rule(self):
        """Cover normal query_rules path with file globbing."""
        result = _call("query_rules", {"query": "behavioral"})
        data = json.loads(result)
        assert isinstance(data, list)
        assert any("core" in item["file"] for item in data)

    def test_query_skips_non_rules_source(self):
        """Cover line 49: skip memory results from non-rules sources."""
        mock_mem = MagicMock(id="m1", kind="semantic", source="tech-stack/react.md", content="behavioral")
        mock_store = MagicMock()
        mock_store.search.return_value = [mock_mem]
        with patch("aizee_mcp.tools.workflow_tools.memory", return_value=mock_store):
            result = _call("query_rules", {"query": "behavioral"})
            data = json.loads(result)
            # The tech-stack source should be skipped, but core.md should still match
            assert isinstance(data, list)

    def test_query_with_rules_source_fts(self):
        """Cover line 51: FTS result from rules source is included."""
        source_path = str(Path("rules/core.md"))
        mock_mem = MagicMock(id="m1", kind="semantic", source=source_path, content="behavioral rules")
        mock_store = MagicMock()
        mock_store.search.return_value = [mock_mem]
        with patch("aizee_mcp.tools.workflow_tools.memory", return_value=mock_store):
            result = _call("query_rules", {"query": "behavioral"})
            data = json.loads(result)
            # core.md should appear (from FTS), and not be duplicated by glob
            files = [item["file"] for item in data]
            assert any("core" in f for f in files)

    def test_query_memory_exception(self):
        """Cover lines 53-54: memory search exception yields empty FTS."""
        with patch("aizee_mcp.tools.workflow_tools.memory", side_effect=Exception("db error")):
            result = _call("query_rules", {"query": "behavioral"})
            data = json.loads(result)
            # Should still find core.md via glob
            assert isinstance(data, list)
            assert any("core" in item["file"] for item in data)

    def test_query_skips_seen_file(self):
        """Cover line 61: file already in seen_files is skipped by glob."""
        # Use OS-native path separator so seen_files matches glob output
        source_path = str(Path("rules/core.md"))
        mock_mem = MagicMock(id="m1", kind="semantic", source=source_path, content="behavioral rules")
        mock_store = MagicMock()
        mock_store.search.return_value = [mock_mem]
        with patch("aizee_mcp.tools.workflow_tools.memory", return_value=mock_store):
            result = _call("query_rules", {"query": "behavioral"})
            data = json.loads(result)
            # core.md should appear only once (FTS result, glob skipped)
            core_count = sum(1 for item in data if "core" in item["file"])
            assert core_count == 1

    def test_query_skips_non_matching_context(self):
        """Cover line 65: rule with non-matching frontmatter is skipped."""
        # scoped.md has paths: [/special/project], query "testing" matches body
        # but context doesn't have matching paths
        result = _call("query_rules", {"query": "testing", "context": {"paths": ["/other/path"]}})
        data = json.loads(result)
        # scoped.md should NOT appear, but always.md should (always: true)
        files = [item["file"] for item in data]
        assert not any("scoped" in f for f in files)
        assert any("always" in f for f in files)

    def test_query_matching_context(self):
        """Cover rule with matching frontmatter is included."""
        result = _call("query_rules", {"query": "testing", "context": {"paths": ["/special/project"]}})
        data = json.loads(result)
        files = [item["file"] for item in data]
        assert any("scoped" in f for f in files)


class TestRunWorkflow:
    def test_invalid_workflow_id(self):
        """Cover lines 73-74: invalid workflow ID."""
        result = _call("run_workflow", {"id": "../etc/passwd"})
        data = json.loads(result)
        assert "error" in data
        assert "Invalid workflow ID" in data["error"]

    def test_run_workflow_success(self):
        """Cover lines 75-76: successful workflow run."""
        mock_k = MagicMock()
        mock_k.run_workflow.return_value = {"status": "completed", "steps": ["s1"]}
        with patch("aizee_mcp.tools.workflow_tools.kernel", return_value=mock_k):
            result = _call("run_workflow", {"id": "deploy"})
            data = json.loads(result)
            assert data["status"] == "completed"

    def test_run_workflow_with_context(self):
        """Cover line 75: workflow with context."""
        mock_k = MagicMock()
        mock_k.run_workflow.return_value = {"status": "completed"}
        with patch("aizee_mcp.tools.workflow_tools.kernel", return_value=mock_k):
            result = _call("run_workflow", {"id": "deploy", "context": {"env": "prod"}})
            data = json.loads(result)
            assert data["status"] == "completed"
            mock_k.run_workflow.assert_called_once_with("deploy", {"env": "prod"})


class TestListRules:
    def test_list_rules(self):
        result = _call("list_rules", {})
        data = json.loads(result)
        assert isinstance(data, list)
        ids = [r["id"] for r in data]
        assert "core" in ids
        assert "scoped" in ids


class TestGetRule:
    def test_existing_rule(self):
        result = _call("get_rule", {"id": "core"})
        data = json.loads(result)
        assert data["exists"] is True
        assert "Core Rules" in data["content"]

    def test_missing_rule(self):
        result = _call("get_rule", {"id": "nonexistent"})
        data = json.loads(result)
        assert data["exists"] is False

    def test_invalid_rule_id(self):
        result = _call("get_rule", {"id": "../../etc/passwd"})
        data = json.loads(result)
        assert data["ok"] is False

    def test_resolve_path_returns_none(self):
        """Cover line 93: resolve_path returns None."""
        with patch("aizee_mcp.tools.workflow_tools.resolve_path", return_value=None):
            result = _call("get_rule", {"id": "core"})
            data = json.loads(result)
            assert data["ok"] is False
            assert "Invalid path" in data["error"]


class TestListWorkflows:
    def test_list_workflows(self):
        result = _call("list_workflows", {})
        data = json.loads(result)
        assert isinstance(data, list)
        ids = [w["id"] for w in data]
        assert "deploy" in ids


class TestGetWorkflow:
    def test_existing_workflow(self):
        result = _call("get_workflow", {"id": "deploy"})
        data = json.loads(result)
        assert data["exists"] is True
        assert "deploy" in data["content"]

    def test_missing_workflow(self):
        result = _call("get_workflow", {"id": "nonexistent"})
        data = json.loads(result)
        assert data["exists"] is False

    def test_invalid_workflow_id(self):
        result = _call("get_workflow", {"id": "../../etc/passwd"})
        data = json.loads(result)
        assert data["ok"] is False

    def test_resolve_path_returns_none(self):
        """Cover line 113: resolve_path returns None."""
        with patch("aizee_mcp.tools.workflow_tools.resolve_path", return_value=None):
            result = _call("get_workflow", {"id": "deploy"})
            data = json.loads(result)
            assert data["ok"] is False
            assert "Invalid path" in data["error"]


class TestRuleResource:
    def test_existing_rule_resource(self):
        """Cover line 126: get_rule_resource returns content."""
        fn = _get_resource_fn("rules")
        assert fn is not None
        os.environ["AIZEE_ROOT"] = _ROOT
        reset_state()
        result = fn("core")
        assert "Core Rules" in result

    def test_unsafe_name_rule_resource(self):
        """Cover line 121: get_rule_resource rejects unsafe name."""
        fn = _get_resource_fn("rules")
        assert fn is not None
        result = fn("../../etc/passwd")
        assert result == ""

    def test_missing_rule_resource(self):
        """Cover line 125: get_rule_resource returns empty for missing file."""
        fn = _get_resource_fn("rules")
        assert fn is not None
        os.environ["AIZEE_ROOT"] = _ROOT
        reset_state()
        result = fn("nonexistent-xyz")
        assert result == ""


class TestWorkflowResource:
    def test_existing_workflow_resource(self):
        """Cover line 136: get_workflow_resource returns content."""
        fn = _get_resource_fn("workflows")
        assert fn is not None
        os.environ["AIZEE_ROOT"] = _ROOT
        reset_state()
        result = fn("deploy")
        assert "deploy" in result

    def test_unsafe_name_workflow_resource(self):
        """Cover line 131: get_workflow_resource rejects unsafe name."""
        fn = _get_resource_fn("workflows")
        assert fn is not None
        result = fn("../../etc/passwd")
        assert result == ""

    def test_missing_workflow_resource(self):
        """Cover line 135: get_workflow_resource returns empty for missing file."""
        fn = _get_resource_fn("workflows")
        assert fn is not None
        os.environ["AIZEE_ROOT"] = _ROOT
        reset_state()
        result = fn("nonexistent-xyz")
        assert result == ""


class TestCompileRuleFiles:
    def test_compile_rule_files(self):
        """Cover lines 141-142: compile rules returns IR."""
        mock_rule = MagicMock()
        mock_rule.file = "rules/core.md"
        mock_rule.obj = "core"
        mock_rule.rules = [MagicMock(), MagicMock()]
        with patch("aizee_mcp.tools.workflow_tools.compile_rules", return_value=[mock_rule]):
            result = _call("compile_rule_files", {})
            data = json.loads(result)
            assert len(data) == 1
            assert data[0]["file"] == "rules/core.md"
            assert data[0]["rules_count"] == 2

    def test_compile_rule_files_with_globs(self):
        """Cover lines 141-142: compile rules with glob patterns."""
        mock_rule = MagicMock()
        mock_rule.file = "rules/core.md"
        mock_rule.obj = "core"
        mock_rule.rules = []
        with patch("aizee_mcp.tools.workflow_tools.compile_rules", return_value=[mock_rule]):
            result = _call("compile_rule_files", {"globs": ["rules/*.md"]})
            data = json.loads(result)
            assert len(data) == 1


class TestRunMcpPlan:
    def test_empty_steps(self):
        """Cover line 152: empty steps rejected."""
        result = _call("run_mcp_plan", {"steps": []})
        data = json.loads(result)
        assert data["ok"] is False
        assert "non-empty list" in data["error"]

    def test_non_list_steps(self):
        """Cover line 151: non-list steps rejected."""
        result = _call("run_mcp_plan", {"steps": "not-a-list"})
        data = json.loads(result)
        assert data["ok"] is False

    def test_invalid_plan(self):
        """Cover line 159: invalid step data raises exception."""
        # Step requires 'id' and 'tool' fields
        result = _call("run_mcp_plan", {"steps": [{"missing": "fields"}]})
        data = json.loads(result)
        assert data["ok"] is False
        assert "Invalid plan" in data["error"]

    def test_valid_plan_execution(self):
        """Cover lines 160-164: valid plan executes via orchestrator."""
        mock_step_result = MagicMock()
        mock_step_result.status.value = "completed"
        mock_step_result.output = "done"
        mock_step_result.error = ""

        with patch("aizee_mcp.tools.workflow_tools.McpAgent"), \
             patch("aizee_mcp.tools.workflow_tools.McpOrchestrator") as mock_orch_cls:
            mock_orch = MagicMock()
            mock_orch.execute = AsyncMock(return_value={"s1": mock_step_result})
            mock_orch_cls.return_value = mock_orch

            result = _call("run_mcp_plan", {"steps": [{"id": "s1", "tool": "read"}]})
            data = json.loads(result)
            assert "s1" in data
            assert data["s1"]["status"] == "completed"
            assert data["s1"]["output"] == "done"

    def test_valid_plan_with_arguments(self):
        """Cover lines 154-157: plan with arguments and depends_on."""
        mock_step_result = MagicMock()
        mock_step_result.status.value = "completed"
        mock_step_result.output = "result"
        mock_step_result.error = ""

        with patch("aizee_mcp.tools.workflow_tools.McpAgent"), \
             patch("aizee_mcp.tools.workflow_tools.McpOrchestrator") as mock_orch_cls:
            mock_orch = MagicMock()
            mock_orch.execute = AsyncMock(return_value={"s1": mock_step_result})
            mock_orch_cls.return_value = mock_orch

            result = _call("run_mcp_plan", {
                "steps": [{"id": "s1", "tool": "read", "arguments": {"file": "test.py"}, "depends_on": []}]
            })
            data = json.loads(result)
            assert data["s1"]["status"] == "completed"
