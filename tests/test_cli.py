"""Comprehensive tests for aizee_cli.py."""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from aizee_cli import main
from memory.store import MemoryStore
from runtime.kernel import Kernel

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tmp_root(with_vector: bool = False) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="aizee_cli_test_"))
    for sub in ("runtime/policies", "workflows", "rules", "tech-stack", "state", "brain"):
        (tmp / sub).mkdir(parents=True, exist_ok=True)
    (tmp / "runtime/policies/default.yaml").write_text(
        "default_action: ask\nrules:\n"
        "  - name: allow-read\n    condition: \"type == 'Read'\"\n    action: allow\n"
    )
    (tmp / "workflows/test.md").write_text(
        "[WORKFLOW] test\n[OBJ] Test workflow for CLI tests.\n[RULES]\n1. [REQ] Step one.\n"
    )
    (tmp / "rules/core.md").write_text("# Core rules\nAgent guidelines.")
    return tmp


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

class TestCliStatus:
    def test_status_returns_zero(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "status"])
            captured = capsys.readouterr()
            assert rc == 0
            assert "aiZee Status" in captured.out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# version
# ---------------------------------------------------------------------------

class TestCliVersion:
    def test_version_output(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "version"])
            captured = capsys.readouterr()
            assert rc == 0
            assert "aiZee" in captured.out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# doctor
# ---------------------------------------------------------------------------

class TestCliDoctor:
    def test_doctor_ok(self, capsys):
        tmp = _tmp_root()
        try:
            main(["--root", str(tmp), "doctor"])
            captured = capsys.readouterr()
            assert "aiZee Doctor" in captured.out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------

class TestCliCheck:
    def test_check_allowed(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "check", "Read"])
            captured = capsys.readouterr()
            assert rc == 0
            assert "allow" in captured.out.lower()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_check_with_args(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "check", "Read", "--args", '{"user": "alice"}'])
            assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_check_with_approve_flag(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "check", "deploy", "--approve"])
            assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# run (workflow)
# ---------------------------------------------------------------------------

class TestCliRun:
    def test_run_workflow(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "run", "test"])
            capsys.readouterr()
            assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_run_workflow_with_context(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "run", "test", "--context", '{"key": "val"}'])
            assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# memory search
# ---------------------------------------------------------------------------

class TestCliMemorySearch:
    def test_memory_search_empty(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "memory", "search", "--query", "nonexistent"])
            captured = capsys.readouterr()
            assert rc == 0
            assert "Memory Search" in captured.out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_memory_search_with_kind(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "memory", "search", "--query", "rules", "--kind", "semantic"])
            assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# memory vector
# ---------------------------------------------------------------------------

class TestCliMemoryVector:
    def test_memory_vector_no_results(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "memory", "vector", "--query", "test"])
            captured = capsys.readouterr()
            assert rc == 0
            assert "Vector Search" in captured.out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_memory_vector_with_kind(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "memory", "vector", "--query", "test", "--kind", "factual"])
            assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# memory add
# ---------------------------------------------------------------------------

class TestCliMemoryAdd:
    def test_memory_add(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main([
                "--root", str(tmp), "memory", "add",
                "--kind", "episodic",
                "--content", "Test memory content",
                "--source", "test-source",
            ])
            captured = capsys.readouterr()
            assert rc == 0
            assert "Added memory" in captured.out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_memory_add_missing_required_args(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "memory", "add"])
            assert rc == 1
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# memory ingest
# ---------------------------------------------------------------------------

class TestCliMemoryIngest:
    def test_memory_ingest(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "memory", "ingest"])
            captured = capsys.readouterr()
            assert rc == 0
            assert "Ingested" in captured.out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# query (hybrid search)
# ---------------------------------------------------------------------------

class TestCliQuery:
    def test_query_returns_table(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "query", "agent rules"])
            captured = capsys.readouterr()
            assert rc == 0
            assert "Hybrid Context Query" in captured.out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_query_with_kind_filter(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "query", "rules", "--kind", "semantic"])
            assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_query_with_limit(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "query", "rules", "--limit", "5"])
            assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# policy
# ---------------------------------------------------------------------------

class TestCliPolicy:
    def test_policy_test_dry_run(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "policy", "test", "Read"])
            captured = capsys.readouterr()
            assert rc == 0
            assert "decision" in captured.out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# budget
# ---------------------------------------------------------------------------

class TestCliBudget:
    def test_budget_list(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "budget", "list"])
            captured = capsys.readouterr()
            assert rc == 0
            assert "Budgets" in captured.out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_budget_set(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main([
                "--root", str(tmp), "budget", "set",
                "--scope", "test", "--max-tokens", "1000",
                "--period", "daily",
            ])
            assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# project
# ---------------------------------------------------------------------------

class TestCliProject:
    def test_project_init(self):
        tmp = Path(tempfile.mkdtemp(prefix="aios_project_test_"))
        try:
            rc = main(["project", "init", "--path", str(tmp)])
            assert rc == 0
            assert (tmp / ".ai" / "active-context.md").exists()
            assert (tmp / "runtime" / "policies" / "default.yaml").exists()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# no command → help
# ---------------------------------------------------------------------------

class TestCliNoCommand:
    def test_no_command_returns_1(self):
        rc = main([])
        assert rc == 1


# ---------------------------------------------------------------------------
# check — blocked action (line 67)
# ---------------------------------------------------------------------------

class TestCliCheckBlocked:
    def test_check_blocked_action(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "check", "Bash", "--args", '{"command": "rm -rf /"}'])
            captured = capsys.readouterr()
            assert rc == 0
            assert "Blocked" in captured.out or "Denied" in captured.out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# _project_root with Path arg (line 32)
# ---------------------------------------------------------------------------

class TestCliProjectRootPath:
    def test_project_root_with_path_arg(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "--project", str(tmp), "status"])
            assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# sync (lines 135-137)
# ---------------------------------------------------------------------------

class TestCliSync:
    def test_sync_runs_subprocess(self, capsys):
        tmp = _tmp_root()
        try:
            with patch("aizee_cli.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                rc = main(["--root", str(tmp), "sync"])
                assert rc == 0
                mock_run.assert_called_once()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# graphify (lines 141-142)
# ---------------------------------------------------------------------------

class TestCliGraphify:
    def test_graphify_runs_subprocess(self, capsys):
        tmp = _tmp_root()
        try:
            with patch("aizee_cli.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                rc = main(["--root", str(tmp), "graphify"])
                assert rc == 0
                mock_run.assert_called_once_with(["graphify", "update", "."], check=False)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# budget usage (lines 176-190)
# ---------------------------------------------------------------------------

class TestCliBudgetUsage:
    def test_budget_usage(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "budget", "usage"])
            captured = capsys.readouterr()
            assert rc == 0
            assert "Budget Usage" in captured.out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# saga (lines 224-229)
# ---------------------------------------------------------------------------

class TestCliSaga:
    def test_saga_run(self, capsys):
        tmp = _tmp_root()
        try:
            steps = '[{"action": "Read", "args": {}}]'
            rc = main(["--root", str(tmp), "saga", "test-saga", "--steps", steps])
            capsys.readouterr()
            assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_saga_run_with_context(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "saga", "test-saga", "--context", '{"key": "val"}'])
            assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# telemetry (lines 233-243)
# ---------------------------------------------------------------------------

class TestCliTelemetry:
    def test_telemetry_summary(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "telemetry", "summary"])
            capsys.readouterr()
            assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_telemetry_events(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "telemetry", "events", "--limit", "5"])
            capsys.readouterr()
            assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_telemetry_system(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "telemetry", "system"])
            capsys.readouterr()
            assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# stack (lines 247-259)
# ---------------------------------------------------------------------------

class TestCliStack:
    def test_stack_detect(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "stack", "detect"])
            capsys.readouterr()
            assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_stack_show(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "stack", "show"])
            capsys.readouterr()
            assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# linkedin (lines 264-291)
# ---------------------------------------------------------------------------

class TestCliLinkedin:
    def _make_args(self, tmp, action, **kwargs):
        """Create a mock args namespace with all linkedin attributes."""
        args = MagicMock()
        args.root = tmp
        args.project = None
        args.linkedin_action = action
        args.text = kwargs.get("text", "")
        args.visibility = kwargs.get("visibility", "PUBLIC")
        args.status = kwargs.get("status", "")
        args.draft_id = kwargs.get("draft_id", "")
        args.when = kwargs.get("when", "")
        args.urn = kwargs.get("urn", "")
        return args

    def test_linkedin_not_configured(self, capsys):
        tmp = _tmp_root()
        try:
            with patch("runtime.mcp_client.McpClient") as mock_cls:
                mock_client = MagicMock()
                mock_client.is_configured.return_value = False
                mock_cls.return_value = mock_client
                from aizee_cli import cmd_linkedin
                rc = cmd_linkedin(self._make_args(tmp, "profile"))
                captured = capsys.readouterr()
                assert rc == 1
                assert "not configured" in captured.out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_linkedin_profile(self, capsys):
        tmp = _tmp_root()
        try:
            with patch("runtime.mcp_client.McpClient") as mock_cls:
                mock_client = MagicMock()
                mock_client.is_configured.return_value = True
                mock_client.call_tool.return_value = {"name": "John"}
                mock_cls.return_value = mock_client
                from aizee_cli import cmd_linkedin
                rc = cmd_linkedin(self._make_args(tmp, "profile"))
                assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_linkedin_post(self, capsys):
        tmp = _tmp_root()
        try:
            with patch("runtime.mcp_client.McpClient") as mock_cls:
                mock_client = MagicMock()
                mock_client.is_configured.return_value = True
                mock_client.call_tool.return_value = {"ok": True}
                mock_cls.return_value = mock_client
                from aizee_cli import cmd_linkedin
                rc = cmd_linkedin(self._make_args(tmp, "post", text="Hello LinkedIn"))
                assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_linkedin_draft(self, capsys):
        tmp = _tmp_root()
        try:
            with patch("runtime.mcp_client.McpClient") as mock_cls:
                mock_client = MagicMock()
                mock_client.is_configured.return_value = True
                mock_client.call_tool.return_value = {"draft_id": "d1"}
                mock_cls.return_value = mock_client
                from aizee_cli import cmd_linkedin
                rc = cmd_linkedin(self._make_args(tmp, "draft", text="Draft text"))
                assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_linkedin_drafts(self, capsys):
        tmp = _tmp_root()
        try:
            with patch("runtime.mcp_client.McpClient") as mock_cls:
                mock_client = MagicMock()
                mock_client.is_configured.return_value = True
                mock_client.call_tool.return_value = {"drafts": []}
                mock_cls.return_value = mock_client
                from aizee_cli import cmd_linkedin
                rc = cmd_linkedin(self._make_args(tmp, "drafts"))
                assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_linkedin_approve(self, capsys):
        tmp = _tmp_root()
        try:
            with patch("runtime.mcp_client.McpClient") as mock_cls:
                mock_client = MagicMock()
                mock_client.is_configured.return_value = True
                mock_client.call_tool.return_value = {"ok": True}
                mock_cls.return_value = mock_client
                from aizee_cli import cmd_linkedin
                rc = cmd_linkedin(self._make_args(tmp, "approve", draft_id="d1"))
                assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_linkedin_publish(self, capsys):
        tmp = _tmp_root()
        try:
            with patch("runtime.mcp_client.McpClient") as mock_cls:
                mock_client = MagicMock()
                mock_client.is_configured.return_value = True
                mock_client.call_tool.return_value = {"ok": True}
                mock_cls.return_value = mock_client
                from aizee_cli import cmd_linkedin
                rc = cmd_linkedin(self._make_args(tmp, "publish", draft_id="d1"))
                assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_linkedin_schedule(self, capsys):
        tmp = _tmp_root()
        try:
            with patch("runtime.mcp_client.McpClient") as mock_cls:
                mock_client = MagicMock()
                mock_client.is_configured.return_value = True
                mock_client.call_tool.return_value = {"ok": True}
                mock_cls.return_value = mock_client
                from aizee_cli import cmd_linkedin
                rc = cmd_linkedin(self._make_args(tmp, "schedule", draft_id="d1", when="2026-07-02T09:00:00Z"))
                assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_linkedin_stats(self, capsys):
        tmp = _tmp_root()
        try:
            with patch("runtime.mcp_client.McpClient") as mock_cls:
                mock_client = MagicMock()
                mock_client.is_configured.return_value = True
                mock_client.call_tool.return_value = {"likes": 10}
                mock_cls.return_value = mock_client
                from aizee_cli import cmd_linkedin
                rc = cmd_linkedin(self._make_args(tmp, "stats", urn="urn:li:post:123"))
                assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_linkedin_delete(self, capsys):
        tmp = _tmp_root()
        try:
            with patch("runtime.mcp_client.McpClient") as mock_cls:
                mock_client = MagicMock()
                mock_client.is_configured.return_value = True
                mock_client.call_tool.return_value = {"ok": True}
                mock_cls.return_value = mock_client
                from aizee_cli import cmd_linkedin
                rc = cmd_linkedin(self._make_args(tmp, "delete", urn="urn:li:post:123"))
                assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# mcp (lines 295-317)
# ---------------------------------------------------------------------------

class TestCliMcp:
    def test_mcp_no_args(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "mcp"])
            captured = capsys.readouterr()
            assert rc == 1
            assert "Usage" in captured.out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_mcp_server_not_configured(self, capsys):
        tmp = _tmp_root()
        try:
            with patch("runtime.mcp_client.McpClient") as mock_cls:
                mock_client = MagicMock()
                mock_client.is_configured.return_value = False
                mock_cls.return_value = mock_client
                rc = main(["--root", str(tmp), "mcp", "test-server", "test-tool"])
                captured = capsys.readouterr()
                assert rc == 1
                assert "not configured" in captured.out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_mcp_call_tool_success(self, capsys):
        tmp = _tmp_root()
        try:
            with patch("runtime.mcp_client.McpClient") as mock_cls:
                mock_client = MagicMock()
                mock_client.is_configured.return_value = True
                mock_client.call_tool.return_value = {"ok": True, "result": "data"}
                mock_cls.return_value = mock_client
                rc = main(["--root", str(tmp), "mcp", "test-server", "test-tool", "--args", '{"key": "val"}'])
                assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_mcp_call_tool_failure(self, capsys):
        tmp = _tmp_root()
        try:
            with patch("runtime.mcp_client.McpClient") as mock_cls:
                mock_client = MagicMock()
                mock_client.is_configured.return_value = True
                mock_client.call_tool.return_value = {"ok": False, "error": "failed"}
                mock_cls.return_value = mock_client
                rc = main(["--root", str(tmp), "mcp", "test-server", "test-tool"])
                assert rc == 1
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_mcp_sync(self, capsys):
        tmp = _tmp_root()
        try:
            with patch("subprocess.call", return_value=0) as mock_call:
                rc = main(["--root", str(tmp), "mcp", "sync"])
                assert rc == 0
                mock_call.assert_called_once()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_mcp_sync_check(self, capsys):
        tmp = _tmp_root()
        try:
            with patch("subprocess.call", return_value=0) as mock_call:
                rc = main(["--root", str(tmp), "mcp", "sync", "--check"])
                assert rc == 0
                # Check that --check was appended
                called_args = mock_call.call_args
                assert "--check" in called_args[0][0]
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# chat (lines 321-336)
# ---------------------------------------------------------------------------

class TestCliChat:
    def test_chat_with_message(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "chat", "hello"])
            capsys.readouterr()
            assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_chat_repl_exit(self, capsys, monkeypatch):
        tmp = _tmp_root()
        try:
            # Simulate user typing "exit"
            monkeypatch.setattr("builtins.input", lambda *a: "exit")
            rc = main(["--root", str(tmp), "chat"])
            assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_chat_repl_eof(self, capsys, monkeypatch):
        tmp = _tmp_root()
        try:
            # Simulate EOF
            monkeypatch.setattr("builtins.input", lambda *a: (_ for _ in ()).throw(EOFError))
            rc = main(["--root", str(tmp), "chat"])
            assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# ci (lines 340-347)
# ---------------------------------------------------------------------------

class TestCliCi:
    def test_ci_run(self, capsys):
        tmp = _tmp_root()
        try:
            with patch("runtime.ci.CIPipeline") as mock_pipeline_cls:
                mock_pipeline = MagicMock()
                mock_pipeline.run.return_value = 0
                mock_pipeline.results = [{"name": "ruff", "ok": True}, {"name": "mypy", "ok": False}]
                mock_pipeline_cls.return_value = mock_pipeline
                rc = main(["--root", str(tmp), "ci"])
                captured = capsys.readouterr()
                assert rc == 0
                assert "PASS" in captured.out
                assert "FAIL" in captured.out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_ci_skip_pytest(self, capsys):
        tmp = _tmp_root()
        try:
            with patch("runtime.ci.CIPipeline") as mock_pipeline_cls:
                mock_pipeline = MagicMock()
                mock_pipeline.run.return_value = 0
                mock_pipeline.results = [{"name": "ruff", "ok": True}]
                mock_pipeline_cls.return_value = mock_pipeline
                rc = main(["--root", str(tmp), "ci", "--skip-pytest"])
                assert rc == 0
                mock_pipeline.run.assert_called_once_with(skip_pytest=True)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# agent (lines 351-365)
# ---------------------------------------------------------------------------

class TestCliAgent:
    def test_agent_spawn(self, capsys):
        tmp = _tmp_root()
        try:
            with patch.object(Kernel, "spawn_agent", return_value={"ok": True}):
                rc = main(["--root", str(tmp), "agent", "spawn", "--agent-id", "a1", "--persona", "ARCH"])
                capsys.readouterr()
                assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_agent_delegate(self, capsys):
        tmp = _tmp_root()
        try:
            with patch.object(Kernel, "delegate", return_value={"ok": True}):
                rc = main(["--root", str(tmp), "agent", "delegate", "--agent-id", "a1", "--action", "Read"])
                capsys.readouterr()
                assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_agent_list(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "agent", "list"])
            capsys.readouterr()
            assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_agent_sync(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "agent", "sync"])
            capsys.readouterr()
            assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# persona (lines 369-382)
# ---------------------------------------------------------------------------

class TestCliPersona:
    def test_persona_list(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "persona", "list"])
            capsys.readouterr()
            assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_persona_detect_multi(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "persona", "detect", "Design", "a", "microservices", "architecture"])
            capsys.readouterr()
            assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_persona_detect_single(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "persona", "detect", "--single", "Audit", "for", "SQL", "injection"])
            capsys.readouterr()
            assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_persona_detect_no_text(self, capsys):
        tmp = _tmp_root()
        try:
            # argparse with nargs="+" requires at least one arg, but we can
            # test the empty text path by passing a single empty string
            # Actually nargs="+" requires at least one arg, so this tests
            # the " ".join(args.text) == "" path
            rc = main(["--root", str(tmp), "persona", "detect", ""])
            capsys.readouterr()
            assert rc == 1
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# skill (lines 386-402)
# ---------------------------------------------------------------------------

class TestCliSkill:
    def test_skill_list(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "skill", "list"])
            capsys.readouterr()
            assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_skill_invoke_not_found(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "skill", "invoke", "nonexistent-skill"])
            captured = capsys.readouterr()
            assert rc == 1
            assert "not found" in captured.out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_skill_search(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "skill", "search", "test"])
            capsys.readouterr()
            assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# doctor — version check, encryption, deps, vector, mcp config
# (lines 432-433, 442-445, 448-449, 456-457, 464-465, 472, 479-481)
# ---------------------------------------------------------------------------

class TestCliDoctorExtended:
    def test_doctor_with_version_file(self, capsys):
        tmp = _tmp_root()
        try:
            (tmp / ".aizee-version").write_text("5.0.0", encoding="utf-8")
            main(["--root", str(tmp), "doctor"])
            captured = capsys.readouterr()
            assert "aiZee Doctor" in captured.out
            assert "5.0.0" in captured.out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_doctor_with_encryption_key(self, capsys, monkeypatch):
        tmp = _tmp_root()
        try:
            monkeypatch.setenv("AIOS_ENCRYPTION_KEY", "invalid-key-that-will-fail")
            main(["--root", str(tmp), "doctor"])
            captured = capsys.readouterr()
            assert "aiZee Doctor" in captured.out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
            monkeypatch.delenv("AIOS_ENCRYPTION_KEY", raising=False)


# ---------------------------------------------------------------------------
# test command (lines 501-530)
# ---------------------------------------------------------------------------

class TestCliTest:
    def test_test_fast(self, capsys):
        tmp = _tmp_root()
        try:
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                rc = main(["--root", str(tmp), "test"])
                captured = capsys.readouterr()
                assert rc == 0
                assert "FAST" in captured.out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_test_full(self, capsys):
        tmp = _tmp_root()
        try:
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                rc = main(["--root", str(tmp), "test", "--full"])
                captured = capsys.readouterr()
                assert rc == 0
                assert "FULL" in captured.out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_test_verbose(self, capsys):
        tmp = _tmp_root()
        try:
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                rc = main(["--root", str(tmp), "test", "--verbose"])
                assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# __main__ block (line 710)
# ---------------------------------------------------------------------------

class TestCliMain:
    def test_main_block_raises_system_exit(self):
        """Line 710: __main__ block raises SystemExit."""
        import subprocess
        import sys
        tmp = _tmp_root()
        try:
            env = dict(os.environ)
            env.update({
                "AIZEE_ROOT": str(tmp),
                "PYTHONIOENCODING": "utf-8",
                "PYTHONHASHSEED": "0",
                "PYTHONPATH": str(Path(__file__).resolve().parent.parent),
            })
            result = subprocess.run(
                [sys.executable, str(Path(__file__).resolve().parent.parent / "aizee_cli.py"), "version"],
                env=env,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0 and "HashRandomization" in result.stderr:  # pragma: no cover
                pytest.skip("Windows subprocess hash randomization issue")
            assert "aiZee" in result.stdout
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# memory search with results (line 106)
# ---------------------------------------------------------------------------

class TestCliMemorySearchWithResults:
    def test_memory_search_with_results(self, capsys):
        tmp = _tmp_root()
        try:
            mock_mem = MagicMock()
            mock_mem.kind = "semantic"
            mock_mem.content = "Test memory content for search"
            with patch.object(MemoryStore, "search", return_value=[mock_mem]):
                rc = main(["--root", str(tmp), "memory", "search", "--query", "test"])
                captured = capsys.readouterr()
                assert rc == 0
                assert "Memory Search" in captured.out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# memory vector with results (lines 115-118)
# ---------------------------------------------------------------------------

class TestCliMemoryVectorWithResults:
    def test_memory_vector_with_results(self, capsys):
        from memory.store import MemoryStore
        tmp = _tmp_root()
        try:
            mock_vr = {"id": 1, "score": 0.95}
            mock_fetched = MagicMock()
            mock_fetched.kind = "factual"
            mock_fetched.source = "test-source"
            with patch.object(MemoryStore, "search_vector", return_value=[mock_vr]), \
                 patch.object(MemoryStore, "get", return_value=mock_fetched):
                rc = main(["--root", str(tmp), "memory", "vector", "--query", "test"])
                captured = capsys.readouterr()
                assert rc == 0
                assert "Vector Search" in captured.out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_memory_vector_results_no_fetched(self, capsys):
        from memory.store import MemoryStore
        tmp = _tmp_root()
        try:
            mock_vr = {"id": 1, "score": 0.95}
            with patch.object(MemoryStore, "search_vector", return_value=[mock_vr]), \
                 patch.object(MemoryStore, "get", return_value=None):
                rc = main(["--root", str(tmp), "memory", "vector", "--query", "test"])
                assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# stack show with docs (lines 256-258)
# ---------------------------------------------------------------------------

class TestCliStackShowWithDocs:
    def test_stack_show_with_docs(self, capsys):
        tmp = _tmp_root()
        try:
            with patch("runtime.tech_stack.load_stack_docs",
                       return_value={"react.md": "React framework content here"}):
                rc = main(["--root", str(tmp), "stack", "show"])
                captured = capsys.readouterr()
                assert rc == 0
                assert "react.md" in captured.out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# linkedin unknown action (lines 285-286)
# ---------------------------------------------------------------------------

class TestCliLinkedinUnknownAction:
    def test_linkedin_unknown_action(self, capsys):
        tmp = _tmp_root()
        try:
            with patch("runtime.mcp_client.McpClient") as mock_cls:
                mock_client = MagicMock()
                mock_client.is_configured.return_value = True
                mock_cls.return_value = mock_client
                from aizee_cli import cmd_linkedin
                args = MagicMock()
                args.root = tmp
                args.project = None
                args.linkedin_action = "bogus_action"
                args.text = ""
                args.visibility = "PUBLIC"
                args.status = ""
                args.draft_id = ""
                args.when = ""
                args.urn = ""
                rc = cmd_linkedin(args)
                captured = capsys.readouterr()
                assert rc == 1
                assert "Unknown linkedin action" in captured.out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# chat REPL with actual message (lines 334-335)
# ---------------------------------------------------------------------------

class TestCliChatReplWithMessage:
    def test_chat_repl_with_message_then_exit(self, capsys, monkeypatch):
        tmp = _tmp_root()
        try:
            inputs = iter(["hello", "exit"])
            monkeypatch.setattr("builtins.input", lambda *a: next(inputs))
            rc = main(["--root", str(tmp), "chat"])
            assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# skill list with skills (line 390)
# ---------------------------------------------------------------------------

class TestCliSkillListWithSkills:
    def test_skill_list_with_skills(self, capsys):
        tmp = _tmp_root()
        try:
            skills_dir = tmp / "skills"
            skills_dir.mkdir(parents=True, exist_ok=True)
            (skills_dir / "skill-a.md").write_text("Skill A content", encoding="utf-8")
            (skills_dir / "skill-b.md").write_text("Skill B content", encoding="utf-8")
            rc = main(["--root", str(tmp), "skill", "list"])
            captured = capsys.readouterr()
            assert rc == 0
            assert "skill-a" in captured.out
            assert "skill-b" in captured.out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# skill invoke with existing skill (line 396)
# ---------------------------------------------------------------------------

class TestCliSkillInvokeFound:
    def test_skill_invoke_found(self, capsys):
        tmp = _tmp_root()
        try:
            skills_dir = tmp / "skills"
            skills_dir.mkdir(parents=True, exist_ok=True)
            (skills_dir / "my-skill.md").write_text("This is the skill content.", encoding="utf-8")
            rc = main(["--root", str(tmp), "skill", "invoke", "my-skill"])
            captured = capsys.readouterr()
            assert rc == 0
            assert "my-skill" in captured.out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# skill search with matching skills (lines 400-401)
# ---------------------------------------------------------------------------

class TestCliSkillSearchWithMatch:
    def test_skill_search_with_match(self, capsys):
        tmp = _tmp_root()
        try:
            skills_dir = tmp / "skills"
            skills_dir.mkdir(parents=True, exist_ok=True)
            (skills_dir / "test-skill.md").write_text("Test skill", encoding="utf-8")
            (skills_dir / "other-skill.md").write_text("Other skill", encoding="utf-8")
            (skills_dir / "testing.md").write_text("Testing skill", encoding="utf-8")
            rc = main(["--root", str(tmp), "skill", "search", "test"])
            captured = capsys.readouterr()
            assert rc == 0
            assert "test-skill" in captured.out
            assert "testing" in captured.out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# doctor — pip import failure (line 457)
# ---------------------------------------------------------------------------

class TestCliDoctorPipFailure:
    def test_doctor_pip_import_failure(self, capsys):
        tmp = _tmp_root()
        try:
            real_import = __import__

            def selective_import(name, *args, **kwargs):
                if name == "cryptography":
                    raise ImportError("mocked: cryptography not found")
                return real_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=selective_import):
                main(["--root", str(tmp), "doctor"])
                captured = capsys.readouterr()
                assert "aiZee Doctor" in captured.out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# doctor — vector index exception (lines 464-465)
# ---------------------------------------------------------------------------

class TestCliDoctorVectorException:
    def test_doctor_vector_exception(self, capsys):
        tmp = _tmp_root()
        try:
            with patch("memory.vector.VectorMemory", side_effect=Exception("vector error")):
                main(["--root", str(tmp), "doctor"])
                captured = capsys.readouterr()
                assert "aiZee Doctor" in captured.out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# doctor — non-Windows os.name path (line 472)
# ---------------------------------------------------------------------------

class TestCliDoctorNonWindows:
    def test_doctor_non_windows_path(self, capsys):
        """Line 472: non-Windows os.name path in global mcp config check."""
        tmp = _tmp_root()
        try:
            args = MagicMock()
            args.root = tmp
            args.project = tmp
            with patch("os.name", "posix"):
                from aizee_cli import cmd_doctor
                rc = cmd_doctor(args)
                assert rc in (0, 1)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# doctor — global mcp config not found (line 479) and exception (lines 480-481)
# ---------------------------------------------------------------------------

class TestCliDoctorGlobalMcp:
    def test_doctor_global_mcp_not_found(self, capsys):
        """Line 479: global mcp config file doesn't exist."""
        tmp = _tmp_root()
        tmp_appdata = Path(tempfile.mkdtemp(prefix="aios_appdata_"))
        try:
            with patch.dict(os.environ, {"APPDATA": str(tmp_appdata)}):
                main(["--root", str(tmp), "doctor"])
                captured = capsys.readouterr()
                assert "aiZee Doctor" in captured.out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
            shutil.rmtree(tmp_appdata, ignore_errors=True)

    def test_doctor_global_mcp_exception(self, capsys):
        """Lines 480-481: exception during global mcp config check."""
        tmp = _tmp_root()
        tmp_appdata = Path(tempfile.mkdtemp(prefix="aios_appdata_exc_"))
        g_dir = tmp_appdata / "devin"
        g_dir.mkdir(parents=True)
        (g_dir / "mcp_config.json").write_text("invalid json{{{", encoding="utf-8")
        try:
            with patch.dict(os.environ, {"APPDATA": str(tmp_appdata)}):
                main(["--root", str(tmp), "doctor"])
                captured = capsys.readouterr()
                assert "aiZee Doctor" in captured.out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
            shutil.rmtree(tmp_appdata, ignore_errors=True)


# ---------------------------------------------------------------------------
# test --xdist (lines 525-527)
# ---------------------------------------------------------------------------

class TestCliTestXdist:
    def test_test_xdist(self, capsys):
        tmp = _tmp_root()
        try:
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                rc = main(["--root", str(tmp), "test", "--xdist"])
                assert rc == 0
                # Verify -n flag was appended
                called_args = mock_run.call_args[0][0]
                assert "-n" in called_args
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# __main__ block — in-process (line 710)
# ---------------------------------------------------------------------------

class TestCliMainBlockInProcess:
    def test_main_block_in_process(self, monkeypatch):
        """Line 710: __main__ block raises SystemExit in-process."""
        import runpy
        tmp = _tmp_root()
        try:
            monkeypatch.setattr(sys, "argv", ["aizee_cli.py", "--root", str(tmp), "version"])
            with pytest.raises(SystemExit):
                runpy.run_path(
                    str(Path(__file__).resolve().parent.parent / "aizee_cli.py"),
                    run_name="__main__",
                )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
