"""Gap coverage batch 17: final residual arcs across runtime modules.

Covers: workflow CMD-step without act callable, uninstaller backup prompt
non-y/p answers, tree_sitter_provider explicit-extensions arc, tracing_otel
span without attributes (fake opentelemetry), rule_compiler non-code bracket
segment, reasoning_graph second-root-not-longer arc, output_gate
skipped_opener-false arc, mobile_patterns real-file walk, mcp_orchestrator
deadlock with a completed step, llm_attestation PLAINTEXT_EXPLICIT privacy,
funnel_tracker string-name `reached` entries, durable _finalize with pending
step, design_library real-file walk, daemon duplicate-server canonical merge.
"""

from __future__ import annotations

import asyncio
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from runtime.daemon import AizeeDaemon
from runtime.design_library import DesignLibrary
from runtime.durable import DurableExecutor, DurableStep, DurableWorkflow
from runtime.durable import StepStatus as DurableStepStatus
from runtime.enums import StepType
from runtime.funnel_tracker import Funnel
from runtime.llm_attestation import PrivacyMode
from runtime.mcp_orchestrator import McpOrchestrator, Plan, Step, StepStatus
from runtime.mobile_patterns import _iter_files_bounded
from runtime.output_gate import auto_fix
from runtime.reasoning_graph import NodeKind, ReasoningGraph
from runtime.rule_compiler import _parse_rules
from runtime.tracing_otel import record_span
from runtime.tree_sitter_provider import SymbolProvider
from runtime.uninstaller import CategoryAction, UninstallCategory, _ask_backup
from runtime.workflow import WorkflowRunner


class TestWorkflow:
    def test_cmd_step_without_act_returns_ok(self, tmp_path: Path) -> None:
        runner = WorkflowRunner(tmp_path)
        result = runner._execute_step(
            {"type": StepType.CMD, "text": "echo hi"}, {}, act=None
        )
        assert result["status"] == "ok"


class TestUninstallerBackup:
    def _keep_cat(self, tmp_path: Path) -> UninstallCategory:
        real = tmp_path / "keepme"
        real.mkdir()
        cat = UninstallCategory("k", "Keep", [real], is_learned=True)
        assert cat.action == CategoryAction.KEEP
        return cat

    def test_decline_backup_returns_none(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("builtins.input", lambda _p="": "n")
        assert _ask_backup([self._keep_cat(tmp_path)]) is None

    def test_other_answer_returns_none(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("builtins.input", lambda _p="": "maybe")
        assert _ask_backup([self._keep_cat(tmp_path)]) is None


class TestTreeSitterProvider:
    def test_extract_from_directory_explicit_extensions(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("def f():\n    return 1\n", encoding="utf-8")
        provider = SymbolProvider()
        symbols = provider.extract_from_directory(tmp_path, extensions={".py"})
        assert isinstance(symbols, list)


class TestTracingOtel:
    def test_record_span_no_attributes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        span = MagicMock()
        tracer = MagicMock()
        tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=span)
        tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)
        fake_trace = types.SimpleNamespace(get_tracer=MagicMock(return_value=tracer))
        fake_otel = types.ModuleType("opentelemetry")
        fake_otel.trace = fake_trace  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "opentelemetry", fake_otel)
        monkeypatch.setenv("AIZEE_OTEL_ENDPOINT", "http://localhost:4318")
        record_span("op-name")  # attributes=None -> skip attribute loop
        tracer.start_as_current_span.assert_called_once()
        span.set_attribute.assert_not_called()


class TestRuleCompiler:
    def test_bracketed_non_code_segment_skipped(self) -> None:
        # "NOPE" fails _CODE_RE (needs -<digits>), so the code-search loop
        # continues past it and the entry keeps its kind only.
        entries = _parse_rules("[KINDX] [NOPE] description here")
        assert entries


class TestReasoningGraph:
    def test_second_root_not_longer_than_best(self) -> None:
        g = ReasoningGraph()
        g.add_node("r1", NodeKind.FINDING)
        g.add_node("x", NodeKind.ACTION)
        g.add_node("r2", NodeKind.FINDING)
        g.add_edge("r1", "x")
        g.activate("r1")
        g.activate("x")
        g.activate("r2")
        path = g.active_path()
        # r1->x (len 2) is best; r2 alone (len 1) loses the comparison.
        assert path == ["r1", "x"]


class TestOutputGate:
    def test_auto_fix_blank_first_line_no_opener_flag(self) -> None:
        fixed, issues = auto_fix("\nsome body text")
        assert "some body text" in fixed
        assert isinstance(issues, list)


class TestMobilePatterns:
    def test_iter_files_bounded_real_file(self, tmp_path: Path) -> None:
        f = tmp_path / "app.dart"
        f.write_text("void main() {}\n", encoding="utf-8")
        results = _iter_files_bounded(tmp_path)
        assert f in results


class _FailAgent:
    async def call_tool(self, tool: str, args: dict) -> SimpleNamespace:
        return SimpleNamespace(error="boom", result=None)


class TestMcpOrchestrator:
    def test_deadlock_marks_pending_step_failed(self) -> None:
        # s3 depends on a nonexistent step -> pre-failed by _unsatisfiable and
        # removed from pending. s2 depends on s3 (which exists in the plan, so
        # s2 is NOT unsatisfiable) but s3 can never complete -> deadlock loop
        # marks s2 failed; s3's not-in-pending check covers the skip arc.
        orch = McpOrchestrator(_FailAgent())  # type: ignore[arg-type]
        plan = Plan(
            id="p",
            steps=[
                Step(id="s2", tool="t2", depends_on=["s3"]),
                Step(id="s3", tool="t3", depends_on=["ghost"]),
            ],
        )
        results = asyncio.run(orch.execute(plan))
        assert results["s3"].status == StepStatus.FAILED
        assert results["s2"].status == StepStatus.FAILED
        assert "never became ready" in (results["s2"].error or "")


class TestLlmAttestation:
    def test_apply_privacy_plaintext_explicit(self) -> None:
        from runtime.llm_attestation import LlmAttestor

        result = LlmAttestor._apply_privacy(
            PrivacyMode.PLAINTEXT_EXPLICIT, b"hello", {"k": "v"}
        )
        assert result["_privacy"] == PrivacyMode.PLAINTEXT_EXPLICIT.value
        assert result["_content"] == "hello"


class TestFunnelTracker:
    def test_record_reached_by_step_names(self) -> None:
        funnel = Funnel("f")
        funnel.add_step("landing")
        funnel.add_step("signup")
        funnel.record({"step_index": 1, "reached": ["landing", "signup"]})
        assert funnel.steps[0].reached == 1
        assert funnel.steps[1].reached == 1


class TestDurable:
    def test_finalize_pending_step_sets_completed_at(self, tmp_path: Path) -> None:
        ex = DurableExecutor(tmp_path)
        wf = DurableWorkflow(
            workflow_id="w1",
            name="w",
            steps=[DurableStep(step_id="s1", name="s1", status=DurableStepStatus.PENDING)],
        )
        ex._finalize(wf)
        # Not all done, no failures -> status stays running but timestamp set.
        assert wf.status == "running"
        assert wf.completed_at is not None


class TestDesignLibrary:
    def test_detect_project_type_walks_real_file(self, tmp_path: Path) -> None:
        (tmp_path / "dashboard.py").write_text("x = 1\n", encoding="utf-8")
        result = DesignLibrary().detect_project_type(tmp_path)
        assert result is not None


class TestDaemonSync:
    def test_duplicate_server_name_skipped_in_second_config(self, tmp_path: Path) -> None:
        import json

        (tmp_path / ".claude").mkdir()
        (tmp_path / ".claude" / "settings.json").write_text(
            json.dumps({"mcpServers": {}}), encoding="utf-8"
        )
        (tmp_path / "aizee_mcp").mkdir()
        (tmp_path / "aizee_mcp" / "config.json").write_text(
            json.dumps({"mcpServers": {"srv": {"command": "a"}}}), encoding="utf-8"
        )
        (tmp_path / ".devin").mkdir()
        (tmp_path / ".devin" / "mcp_config.json").write_text(
            json.dumps({"mcpServers": {"srv": {"command": "b"}}}), encoding="utf-8"
        )
        daemon = AizeeDaemon(tmp_path)
        changed = daemon._sync_claude_settings({"srv": {"enabled": True}})
        assert changed == 1
        # First config wins for the duplicate name.
        cfg = json.loads((tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8"))
        assert cfg["mcpServers"]["srv"]["command"] == "a"
