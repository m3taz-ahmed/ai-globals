"""Tests for the workflow runner."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from runtime.workflow import Workflow, WorkflowRunner


def _make_workflow(root: Path, wf_id: str, steps: str) -> None:
    wf_dir = root / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    (wf_dir / f"{wf_id}.md").write_text(f"[WORKFLOW] {wf_id}\n\n[OBJ] Test workflow.\n\n{steps}", encoding="utf-8")


def test_load_workflow(tmp_path: Path) -> None:
    _make_workflow(tmp_path, "test", "1. [REQ] Dummy step.")
    runner = WorkflowRunner(tmp_path, os_root=tmp_path)
    wf = runner.get("test")
    assert wf is not None
    assert wf.id == "test"
    assert wf.title == "test"


def test_workflow_run_returns_result(tmp_path: Path) -> None:
    _make_workflow(tmp_path, "simple", "1. [REQ] Plan the task.\n2. [CMD] bash: echo done\n")
    runner = WorkflowRunner(tmp_path, os_root=tmp_path)

    def act(action: str, **kwargs):
        return {"ok": True, "action": action}

    result = runner.run("simple", {}, act=act)
    assert result["ok"]
    assert result["workflow"] == "simple"
    assert len(result["steps"]) == 2


def test_workflow_run_handles_bad_mcp_command(tmp_path: Path) -> None:
    _make_workflow(tmp_path, "bad-mcp", "1. [CMD] mcp: not_a_valid_command\n")
    runner = WorkflowRunner(tmp_path, os_root=tmp_path)
    result = runner.run("bad-mcp", {}, act=lambda **_: {"ok": True})
    assert result["steps"][0]["status"] == "mcp_parse_error"


def test_workflow_persists_state(tmp_path: Path) -> None:
    _make_workflow(tmp_path, "persist", "1. [REQ] Step one.\n")
    runner = WorkflowRunner(tmp_path, os_root=tmp_path)
    runner.run("persist", {}, act=None)
    runs = runner.list_workflows()
    assert "persist" in runs


def test_workflow_not_found(tmp_path: Path) -> None:
    runner = WorkflowRunner(tmp_path, os_root=tmp_path)
    result = runner.run("missing", {}, act=None)
    assert not result["ok"]
    assert "not found" in result["error"]


# ---------------------------------------------------------------------------
# Persona detection in run() — lines 85-90
# ---------------------------------------------------------------------------

def test_workflow_run_detects_personas_from_message(tmp_path: Path) -> None:
    """When context has a 'message' but no 'personas'/'persona', persona detection runs."""
    _make_workflow(tmp_path, "persona", "1. [REQ] Step one.\n")
    runner = WorkflowRunner(tmp_path, os_root=tmp_path)
    mock_detector = MagicMock()
    mock_detector.detect_multiple.return_value = {
        "persona": "architect",
        "skill": "planning",
        "personas": ["architect"],
        "skills": ["planning"],
        "lords": [],
    }
    runner.persona = mock_detector
    result = runner.run("persona", {"message": "build a web app"}, act=None)
    assert result["ok"]
    assert result["context"]["persona"] == "architect"
    assert result["context"]["personas"] == ["architect"]
    mock_detector.detect_multiple.assert_called_once_with("build a web app")


def test_workflow_run_skips_persona_detection_when_already_set(tmp_path: Path) -> None:
    """When context already has 'personas', detection is skipped."""
    _make_workflow(tmp_path, "skip", "1. [REQ] Step one.\n")
    runner = WorkflowRunner(tmp_path, os_root=tmp_path)
    mock_detector = MagicMock()
    runner.persona = mock_detector
    result = runner.run("skip", {"personas": ["existing"], "message": "do something"}, act=None)
    assert result["ok"]
    mock_detector.detect_multiple.assert_not_called()


def test_workflow_run_skips_persona_detection_when_persona_set(tmp_path: Path) -> None:
    """When context already has 'persona', detection is skipped."""
    _make_workflow(tmp_path, "skip2", "1. [REQ] Step one.\n")
    runner = WorkflowRunner(tmp_path, os_root=tmp_path)
    mock_detector = MagicMock()
    runner.persona = mock_detector
    result = runner.run("skip2", {"persona": "dev"}, act=None)
    assert result["ok"]
    mock_detector.detect_multiple.assert_not_called()


def test_workflow_run_skips_persona_detection_when_empty_prompt(tmp_path: Path) -> None:
    """When prompt is empty string, detection is skipped."""
    _make_workflow(tmp_path, "skip3", "1. [REQ] Step one.\n")
    runner = WorkflowRunner(tmp_path, os_root=tmp_path)
    mock_detector = MagicMock()
    runner.persona = mock_detector
    result = runner.run("skip3", {"message": "  "}, act=None)
    assert result["ok"]
    mock_detector.detect_multiple.assert_not_called()


# ---------------------------------------------------------------------------
# _parse_mcp returns parsed tuple — line 134
# ---------------------------------------------------------------------------

def test_parse_mcp_returns_parsed_command(tmp_path: Path) -> None:
    """_parse_mcp returns (server, tool, args) for valid MCP commands."""
    runner = WorkflowRunner(tmp_path, os_root=tmp_path)
    parsed = runner._parse_mcp("server.tool")
    assert parsed is not None
    assert parsed[0] == "server"
    assert parsed[1] == "tool"


# ---------------------------------------------------------------------------
# PROHIBIT step type — lines 155-156
# ---------------------------------------------------------------------------

def test_workflow_prohibit_step(tmp_path: Path) -> None:
    """PROHIBIT steps return 'prohibited' status."""
    _make_workflow(tmp_path, "prohibit", "1. [PROHIBIT] Never do this.\n")
    runner = WorkflowRunner(tmp_path, os_root=tmp_path)
    result = runner.run("prohibit", {}, act=None)
    assert result["ok"]
    assert result["steps"][0]["status"] == "prohibited"


# ---------------------------------------------------------------------------
# Bash command exception — lines 173-175
# ---------------------------------------------------------------------------

def test_workflow_bash_command_exception(tmp_path: Path) -> None:
    """When act() raises for a bash command, status is 'error'."""
    _make_workflow(tmp_path, "bash-err", "1. [CMD] bash: risky command\n")

    def act(action: str, **kwargs):
        raise RuntimeError("boom")

    runner = WorkflowRunner(tmp_path, os_root=tmp_path)
    result = runner.run("bash-err", {}, act=act)
    assert result["steps"][0]["status"] == "error"
    assert result["steps"][0]["evaluation"]["ok"] is False
    assert "boom" in result["steps"][0]["evaluation"]["error"]


# ---------------------------------------------------------------------------
# Bash command denied — line 170 (decision path)
# ---------------------------------------------------------------------------

def test_workflow_bash_command_denied(tmp_path: Path) -> None:
    """When act() returns ok=False, status comes from decision."""
    _make_workflow(tmp_path, "bash-deny", "1. [CMD] bash: blocked\n")

    def act(action: str, **kwargs):
        return {"ok": False, "decision": {"decision": "denied"}}

    runner = WorkflowRunner(tmp_path, os_root=tmp_path)
    result = runner.run("bash-deny", {}, act=act)
    assert result["steps"][0]["status"] == "denied"


# ---------------------------------------------------------------------------
# MCP command: not configured — line 185
# ---------------------------------------------------------------------------

def test_workflow_mcp_not_configured(tmp_path: Path) -> None:
    """MCP command for unconfigured server returns 'mcp_not_configured'."""
    _make_workflow(tmp_path, "mcp-nocfg", "1. [CMD] mcp: unknownsrv.tool\n")
    runner = WorkflowRunner(tmp_path, os_root=tmp_path)
    result = runner.run("mcp-nocfg", {}, act=lambda **_: {"ok": True})
    assert result["steps"][0]["status"] == "mcp_not_configured"


# ---------------------------------------------------------------------------
# MCP command: call_tool success — lines 182-184, 188-194
# ---------------------------------------------------------------------------

def test_workflow_mcp_call_success(tmp_path: Path) -> None:
    """MCP command with configured server and successful call returns 'allowed'."""
    _make_workflow(tmp_path, "mcp-ok", "1. [CMD] mcp: myserver.mytool\n")
    runner = WorkflowRunner(tmp_path, os_root=tmp_path)
    with patch("runtime.workflow.McpClient") as MockClient:
        instance = MockClient.return_value
        instance.is_configured.return_value = True
        instance.call_tool.return_value = {"ok": True, "result": "done"}
        result = runner.run("mcp-ok", {}, act=lambda **_: {"ok": True})
    assert result["steps"][0]["status"] == "allowed"
    assert result["steps"][0]["evaluation"]["ok"] is True


# ---------------------------------------------------------------------------
# MCP command: call_tool failure — line 192
# ---------------------------------------------------------------------------

def test_workflow_mcp_call_failed(tmp_path: Path) -> None:
    """MCP command with configured server but failed call returns 'mcp_call_failed'."""
    _make_workflow(tmp_path, "mcp-fail", "1. [CMD] mcp: myserver.mytool\n")
    runner = WorkflowRunner(tmp_path, os_root=tmp_path)
    with patch("runtime.workflow.McpClient") as MockClient:
        instance = MockClient.return_value
        instance.is_configured.return_value = True
        instance.call_tool.return_value = {"ok": False, "error": "tool error"}
        result = runner.run("mcp-fail", {}, act=lambda **_: {"ok": True})
    assert result["steps"][0]["status"] == "mcp_call_failed"


# ---------------------------------------------------------------------------
# MCP command: call_tool exception — lines 195-197
# ---------------------------------------------------------------------------

def test_workflow_mcp_call_exception(tmp_path: Path) -> None:
    """MCP command where call_tool raises returns 'error'."""
    _make_workflow(tmp_path, "mcp-exc", "1. [CMD] mcp: myserver.mytool\n")
    runner = WorkflowRunner(tmp_path, os_root=tmp_path)
    with patch("runtime.workflow.McpClient") as MockClient:
        instance = MockClient.return_value
        instance.is_configured.return_value = True
        instance.call_tool.side_effect = RuntimeError("connection lost")
        result = runner.run("mcp-exc", {}, act=lambda **_: {"ok": True})
    assert result["steps"][0]["status"] == "error"
    assert "connection lost" in result["steps"][0]["evaluation"]["error"]


# ---------------------------------------------------------------------------
# CMD with no recognized prefix — line 199 (NOOP)
# ---------------------------------------------------------------------------

def test_workflow_cmd_noop(tmp_path: Path) -> None:
    """CMD step without bash:/mcp: prefix returns 'noop'."""
    _make_workflow(tmp_path, "noop", "1. [CMD] do something vague\n")
    runner = WorkflowRunner(tmp_path, os_root=tmp_path)
    result = runner.run("noop", {}, act=lambda **_: {"ok": True})
    assert result["steps"][0]["status"] == "noop"


# ---------------------------------------------------------------------------
# get_run returns None for missing run — line 207
# ---------------------------------------------------------------------------

def test_get_run_returns_none_for_missing(tmp_path: Path) -> None:
    runner = WorkflowRunner(tmp_path, os_root=tmp_path)
    assert runner.get_run("nonexistent-run-id") is None


# ---------------------------------------------------------------------------
# get_run returns data for existing run — lines 208-215
# ---------------------------------------------------------------------------

def test_get_run_returns_data_for_existing(tmp_path: Path) -> None:
    _make_workflow(tmp_path, "getrun", "1. [REQ] Step one.\n")
    runner = WorkflowRunner(tmp_path, os_root=tmp_path)
    result = runner.run("getrun", {}, act=None)
    run_id = result["run_id"]
    data = runner.get_run(run_id)
    assert data is not None
    assert data["workflow_id"] == "getrun"
    assert data["id"] == run_id


# ---------------------------------------------------------------------------
# Workflow.load with different title tags
# ---------------------------------------------------------------------------

def test_workflow_load_with_file_tag(tmp_path: Path) -> None:
    """Workflow.load extracts title from [FILE] tag."""
    wf_dir = tmp_path / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    (wf_dir / "filetag.md").write_text("[FILE] My File Workflow\n\n[OBJ] test.\n", encoding="utf-8")
    wf = Workflow.load(wf_dir / "filetag.md")
    assert wf.title == "My File Workflow"


def test_workflow_load_with_saga_tag(tmp_path: Path) -> None:
    """Workflow.load extracts title from [SAGA] tag."""
    wf_dir = tmp_path / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    (wf_dir / "sagatag.md").write_text("[SAGA] My Saga\n\n[OBJ] test.\n", encoding="utf-8")
    wf = Workflow.load(wf_dir / "sagatag.md")
    assert wf.title == "My Saga"


def test_workflow_load_falls_back_to_stem(tmp_path: Path) -> None:
    """Workflow.load falls back to path stem when no title tag found."""
    wf_dir = tmp_path / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    (wf_dir / "notitle.md").write_text("Just some content without tags.\n", encoding="utf-8")
    wf = Workflow.load(wf_dir / "notitle.md")
    assert wf.title == "notitle"


# ---------------------------------------------------------------------------
# REQ step returns OK — line 159
# ---------------------------------------------------------------------------

def test_workflow_req_step_returns_ok(tmp_path: Path) -> None:
    """REQ steps return 'ok' status."""
    _make_workflow(tmp_path, "reqonly", "1. [REQ] Plan the task.\n")
    runner = WorkflowRunner(tmp_path, os_root=tmp_path)
    result = runner.run("reqonly", {}, act=None)
    assert result["steps"][0]["status"] == "ok"


# ---------------------------------------------------------------------------
# get returns None for missing workflow — line 74
# ---------------------------------------------------------------------------

def test_get_returns_none_for_missing(tmp_path: Path) -> None:
    runner = WorkflowRunner(tmp_path, os_root=tmp_path)
    assert runner.get("nonexistent") is None
