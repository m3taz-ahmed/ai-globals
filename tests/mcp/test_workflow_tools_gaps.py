"""Gap tests for workflow_tools.py — scan caps, glob validation, plan edges."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aizee_mcp._compat import FastMCP

pytestmark = pytest.mark.mcp

_ROOT = tempfile.mkdtemp(prefix="aizee_wf_gap_")
os.environ["AIZEE_ROOT"] = _ROOT
ROOT = Path(_ROOT)
for sub in ("rules", "workflows", "tech-stack", "skills", "state", "brain"):
    (ROOT / sub).mkdir(parents=True, exist_ok=True)
(ROOT / "rules" / "r1.md").write_text("hitword content\n", encoding="utf-8")

from aizee_mcp.tools.common import reset_state  # noqa: E402
from aizee_mcp.tools.workflow_tools import register_workflow_tools  # noqa: E402

_mcp = FastMCP("test-wf-gaps")
register_workflow_tools(_mcp)


def _call(name: str, arguments: dict) -> str:
    os.environ["AIZEE_ROOT"] = _ROOT
    reset_state()
    tool = _mcp._tool_manager.get_tool(name)
    return tool.fn(**arguments)


class TestQueryRulesScanCaps:
    def test_scan_cap_200(self, monkeypatch):
        # fabricate 250 rule paths
        paths = [ROOT / "rules" / f"gen{i:03d}.md" for i in range(250)]
        monkeypatch.setattr(Path, "glob", lambda self, pat: iter(paths) if "rules" in pat else iter([]))
        out = json.loads(_call("query_rules", {"query": "hitword"}))
        assert isinstance(out, list)

    def test_oversize_and_stat_error(self, monkeypatch):
        p_big = ROOT / "rules" / "big.md"
        p_big.write_text("hitword", encoding="utf-8")
        p_err = ROOT / "rules" / "err.md"
        real_stat = Path.stat
        def st(self, *a, **k):
            if self.name == "big.md":
                class S: st_size = 500_000
                return S()
            if self.name == "err.md":
                raise OSError("stat fail")
            return real_stat(self, *a, **k)
        monkeypatch.setattr(Path, "stat", st)
        p_err.write_text("hitword", encoding="utf-8")
        out = json.loads(_call("query_rules", {"query": "hitword"}))
        files = [i["file"] for i in out]
        assert not any("big" in f for f in files)
        assert not any("err" in f for f in files)
        assert any("r1" in f for f in files)

    def test_read_failure_skipped(self, monkeypatch):
        p = ROOT / "rules" / "unreadable.md"
        p.write_text("hitword", encoding="utf-8")
        real_read = Path.read_text
        def rd(self, *a, **k):
            if self.name == "unreadable.md":
                raise OSError("denied")
            return real_read(self, *a, **k)
        monkeypatch.setattr(Path, "read_text", rd)
        out = json.loads(_call("query_rules", {"query": "hitword"}))
        assert not any("unreadable" in i["file"] for i in out)
        assert any("r1" in i["file"] for i in out)


class TestCompileRuleFilesEdges:
    def test_globs_not_list(self):
        data = json.loads(_call("compile_rule_files", {"globs": "x"}))
        assert data["ok"] is False

    def test_globs_too_many(self):
        data = json.loads(_call("compile_rule_files", {"globs": ["a"] * 51}))
        assert data["ok"] is False

    @pytest.mark.parametrize("g", ["", 123, "a" * 300, "../esc", "/abs", "\\abs"])
    def test_invalid_glob_patterns(self, g):
        data = json.loads(_call("compile_rule_files", {"globs": [g]}))
        assert data["ok"] is False
        assert "Invalid glob" in data["error"]

    def test_compile_raises(self):
        with patch("aizee_mcp.tools.workflow_tools.compile_rules", side_effect=RuntimeError("cx")):
            data = json.loads(_call("compile_rule_files", {}))
        assert data["ok"] is False
        assert "compilation failed" in data["error"].lower()


class TestRunMcpPlanEdges:
    def test_too_many_steps(self):
        data = json.loads(_call("run_mcp_plan", {"steps": [{"id": "s", "tool": "t"}] * 51}))
        assert data["ok"] is False
        assert "50" in data["error"]

    def test_all_non_dict_steps(self):
        data = json.loads(_call("run_mcp_plan", {"steps": ["x", 1, None]}))
        assert data["ok"] is False

    def test_nested_event_loop(self):
        async def _nested():
            return _call("run_mcp_plan", {"steps": [{"id": "s", "tool": "t"}]})
        data = json.loads(__import__("asyncio").run(_nested()))
        assert data["ok"] is False
        assert "event loop" in data["error"]

    def test_mixed_dict_steps(self):
        mock_res = MagicMock()
        mock_res.status.value = "completed"
        mock_res.output = "o"
        mock_res.error = ""
        with patch("aizee_mcp.tools.workflow_tools.McpAgent"), \
             patch("aizee_mcp.tools.workflow_tools.McpOrchestrator") as oc:
            oc.return_value.execute_async = AsyncMock(return_value={"s1": mock_res})
            data = json.loads(_call("run_mcp_plan", {"steps": [{"id": "s1", "tool": "read"}, "junk"]}))
        assert data["s1"]["status"] == "completed"
