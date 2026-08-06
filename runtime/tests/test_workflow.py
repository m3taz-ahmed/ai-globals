"""Tests for the workflow runner."""

from __future__ import annotations

from pathlib import Path

from runtime.workflow import WorkflowRunner


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
