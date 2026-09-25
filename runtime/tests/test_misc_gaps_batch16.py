"""Coverage gap tests - batch 16.

Residual branches: uninstaller_gui toggle/refresh/backup arcs,
crm_manager same-stage return, memory/store integrity-key fallthroughs +
decay-table migration early return, dashboard rate LRU eviction +
settings-restart cache flush + SSE broken pipe, blast_radius BFS visited +
existing-credential edge, audit_signing ImportError fallback,
design_slop_verifier SVG finding, cross_tool_taint BFS visited,
confidence_gate weight bounds, agentic_security default args,
prompt_injection_suite containment/should_detect arcs, approval_service
from_dict enum + falsy channel, layers no-violation + key-at-end,
learning_loop explicit args, contract_emitter reraise, commands PENDING,
budget_escalation explicit config, budget_advanced settled-None hold,
audit fallback blank lines, approval_channels small args, memory/hybrid
bm25 miss, config version fallback, seo_tools @graph scalar,
memory_tools seen-id iteration, settings section exits,
spec/engine REMOVED deltas, taint list-scalar arc.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest


class TestUninstallerGuiResidual:
    def _gui(self):
        from runtime.uninstaller_gui import UninstallerGUI

        gui = UninstallerGUI.__new__(UninstallerGUI)
        gui.tree = MagicMock()
        gui.categories = []
        return gui

    def test_toggle_row_no_tags(self) -> None:
        gui = self._gui()
        tree = cast(MagicMock, gui.tree)
        tree.selection.return_value = ("item1",)
        tree.item.return_value = []  # empty tags -> early return
        gui._on_toggle_row()  # must not raise

    def test_refresh_row_unknown_key(self) -> None:
        gui = self._gui()
        tree = cast(MagicMock, gui.tree)
        tree.get_children.return_value = ("item1",)
        tree.item.return_value = ["no-such-category"]
        gui.categories = [cast(Any, SimpleNamespace(key="other", action=None))]
        gui._refresh_all_rows()  # inner for exhausts -> back to outer loop

    def test_confirm_with_backup(self) -> None:
        gui = self._gui()
        gui.backup_var = MagicMock(get=MagicMock(return_value=True))
        gui.backup_path_var = MagicMock(get=MagicMock(return_value="C:/b"))
        with patch("runtime.uninstaller_gui.messagebox") as mb:
            mb.askyesno.return_value = True
            cat = SimpleNamespace(label="L", action=None)
            assert gui._confirm_uninstall([cast(Any, cat)]) is True


class TestCrmSameStage:
    def test_same_nonterminal_stage_returns(self) -> None:
        from runtime.crm_manager import Task, TaskStage

        t = Task(task_id="t1", title="x")
        t.validate_transition(TaskStage.TODO)  # same stage, non-terminal -> return


class TestMemoryStoreKeyFallback:
    def test_ext_key_file_missing_falls_through(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from memory.store import MemoryStore

        monkeypatch.delenv("AIZEE_INTEGRITY_KEY", raising=False)
        monkeypatch.setenv("AIZEE_INTEGRITY_KEY_FILE", str(tmp_path / "nope.key"))
        ms = MemoryStore.__new__(MemoryStore)
        ms.root = tmp_path
        key = ms._load_integrity_key()
        assert len(key) == 64  # generated hex key

    def test_ext_key_file_empty_falls_through(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from memory.store import MemoryStore

        ext = tmp_path / "ext.key"
        ext.write_text("   \n")
        monkeypatch.delenv("AIZEE_INTEGRITY_KEY", raising=False)
        monkeypatch.setenv("AIZEE_INTEGRITY_KEY_FILE", str(ext))
        ms = MemoryStore.__new__(MemoryStore)
        ms.root = tmp_path
        key = ms._load_integrity_key()
        assert len(key) == 64

    def test_key_file_empty_content_regenerates(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import memory.store as store_mod
        from memory.store import MemoryStore

        monkeypatch.delenv("AIZEE_INTEGRITY_KEY", raising=False)
        monkeypatch.delenv("AIZEE_INTEGRITY_KEY_FILE", raising=False)
        key_path = tmp_path / store_mod._INTEGRITY_KEY_RELATIVE
        key_path.parent.mkdir(parents=True, exist_ok=True)
        key_path.write_text("   ")
        ms = MemoryStore.__new__(MemoryStore)
        ms.root = tmp_path
        key = ms._load_integrity_key()
        assert len(key) == 64

    def test_migrate_decay_table_missing(self, tmp_path: Path) -> None:
        import contextlib
        import sqlite3

        from memory.store import MemoryStore

        ms = MemoryStore.__new__(MemoryStore)
        db = tmp_path / "m.db"
        conn = sqlite3.connect(str(db))
        conn.execute("CREATE TABLE t(x)")
        conn.close()

        @contextlib.contextmanager
        def _cm():
            yield sqlite3.connect(str(db))

        ms._conn = _cm
        ms._migrate_decay_table()  # memory_decay absent -> early return


class TestDashboardResidual:
    def test_lru_eviction_after_stale_cleanup(self) -> None:
        import dashboard.server as srv

        saved = dict(srv._rate_state)
        try:
            srv._rate_state.clear()
            # fill > 90% with fresh entries + 1 stale
            now = 1_000_000.0
            for i in range(int(srv._rate_max_entries * 0.9) + 5):
                srv._rate_state[f"ip{i}"] = (1, now)
            srv._rate_state["stale"] = (1, now - srv._rate_window - 1)
            srv._evict_stale_entries(now)
            assert "stale" not in srv._rate_state
            assert len(srv._rate_state) <= srv._rate_max_entries * 0.9
        finally:
            srv._rate_state.clear()
            srv._rate_state.update(saved)

    def test_settings_restart_flushes_caches(self) -> None:
        import dashboard.server as srv

        handler = srv.DashboardHandler.__new__(srv.DashboardHandler)
        handler._send = MagicMock()
        k = MagicMock()
        m = MagicMock()
        srv._kernel_cache = (Path("x"), k)
        srv._memory_cache = (Path("y"), m)
        try:
            handler._send_settings_restart()
            k.save.assert_called_once()
            m.close.assert_called_once()
            assert srv._kernel_cache is None
            assert srv._memory_cache is None
        finally:
            srv._kernel_cache = None
            srv._memory_cache = None

    def test_sse_broken_pipe_finally(self) -> None:
        import dashboard.server as srv

        handler = srv.DashboardHandler.__new__(srv.DashboardHandler)
        handler._send = MagicMock()
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler._origin = MagicMock(return_value=None)
        handler.kernel = MagicMock()
        handler.kernel.status.return_value = {}
        handler.wfile = MagicMock()
        handler.wfile.write.side_effect = BrokenPipeError
        srv.DashboardHandler._sse_clients = 0
        handler._send_sse_events()  # broken pipe swallowed, client count decremented
        assert srv.DashboardHandler._sse_clients == 0


class TestBlastRadiusResidual:
    def test_bfs_visited_skip(self) -> None:
        from runtime.blast_radius import _reachable_nodes

        adj = {"S": [("A", ""), ("B", "")], "A": [("C", "")], "B": [("C", "")]}
        out = _reachable_nodes(cast(Any, adj), "S")
        assert out == {"S", "A", "B", "C"}

    def test_existing_credential_skips_add(self) -> None:
        from runtime.blast_radius import BlastRadiusGraph

        br = BlastRadiusGraph()
        br.add_agent("a1", [], ["shared-cred"])
        br.add_agent("a2", [], ["shared-cred"])  # cred already in _nodes
        assert "cred:shared-cred" in br._nodes


class TestAuditSigningFallback:
    def test_import_error_fallback(self) -> None:
        import builtins
        import importlib

        import runtime.audit_signing as m

        real_import = builtins.__import__

        def fake_import(name, *a, **k):
            if name.startswith("cryptography"):
                raise ImportError("blocked")
            return real_import(name, *a, **k)

        try:
            with patch.object(builtins, "__import__", side_effect=fake_import):
                importlib.reload(m)
            assert m._HAS_CRYPTOGRAPHY is False
        finally:
            importlib.reload(m)
        assert m._HAS_CRYPTOGRAPHY is True


class TestDesignSlopSvg:
    def test_svg_illustration_finding(self) -> None:
        from runtime.design_slop_verifier import DesignSlopVerifier

        v = DesignSlopVerifier()
        html = '<div><svg class="undraw-hero"></svg></div>'
        findings = v._check_svg_illustrations(html)
        assert findings and findings[0].category.value == "svg_illustrations"


class TestCrossToolTaintVisited:
    def test_visited_state_skip(self) -> None:
        from runtime.cross_tool_taint import (
            DataClassification,
            ToolCall,
            _find_path_through_sensitive,
        )

        def mk(cid: str) -> ToolCall:
            return ToolCall(
                call_id=cid, tool_name="t", args={}, result=None,
                classification=DataClassification.NORMAL, timestamp=0.0,
            )

        calls = {c: mk(c) for c in ("S", "A", "B", "C")}
        adj = {"S": [("A", ""), ("B", "")], "A": [("C", "")], "B": [("C", "")]}
        out = _find_path_through_sensitive("S", "", set(), calls, adj)
        assert out is None


class TestConfidenceGateWeight:
    def test_weight_out_of_range(self) -> None:
        from runtime.confidence_gate import ConfidenceGate, Evidence

        g = ConfidenceGate(threshold=0.5)
        with pytest.raises(ValueError):
            g.add_evidence(Evidence(source="s", passed=True, weight=1.5))


class TestAgenticSecurityDefaults:
    def test_scan_directory_defaults(self, tmp_path: Path) -> None:
        from runtime.agentic_security import AgenticSecurityScanner

        (tmp_path / "a.py").write_text("x = 1")
        scanner = AgenticSecurityScanner()
        report = scanner.scan_directory(tmp_path)  # default ext/exclude sets
        assert report is not None


class TestPromptInjectionSuiteResidual:
    def test_detected_but_escalate_not_contained(self) -> None:
        from eval.prompt_injection_suite import AttackCase, PromptInjectionEvalSuite
        from runtime.defensive_injection import DefenseResult, DefenseStrategy

        detector = MagicMock()
        verdict = MagicMock()
        verdict.is_injection = True
        detector.detect.return_value = verdict
        injector = MagicMock()
        injector.inject.return_value = DefenseResult(
            original_prompt="x", hardened_prompt="h",
            strategy=DefenseStrategy.ESCALATE,
            techniques_addressed=(), redirect_message="", sanitized=False,
        )
        suite = PromptInjectionEvalSuite(detector=detector, injector=injector)
        case = AttackCase(technique=suite.ATTACK_CORPUS[0].technique, text="x",
                          description="d")
        with patch.object(PromptInjectionEvalSuite, "ATTACK_CORPUS", [case]):
            with patch.object(PromptInjectionEvalSuite, "BENIGN_CORPUS", []):
                report = suite.run()
        assert report.detected_attacks == 1
        assert report.contained_attacks == 0

    def test_not_detected_and_not_expected(self) -> None:
        from eval.prompt_injection_suite import AttackCase, PromptInjectionEvalSuite

        detector = MagicMock()
        verdict = MagicMock()
        verdict.is_injection = False
        detector.detect.return_value = verdict
        injector = MagicMock()
        suite = PromptInjectionEvalSuite(detector=detector, injector=injector)
        case = AttackCase(technique=suite.ATTACK_CORPUS[0].technique, text="x",
                          description="d", should_detect=False)
        with patch.object(PromptInjectionEvalSuite, "ATTACK_CORPUS", [case]):
            with patch.object(PromptInjectionEvalSuite, "BENIGN_CORPUS", []):
                report = suite.run()
        assert report.missed_attacks == []


class TestApprovalServiceResidual:
    def test_from_dict_enum_status(self) -> None:
        from runtime.approval_service import ApprovalRequest, ApprovalStatus

        req = ApprovalRequest(
            id="r1", action="a", args={}, reason="r",
            status=ApprovalStatus.PENDING,
        )
        d = req.to_dict()
        d["status"] = ApprovalStatus.APPROVED  # already enum, not str
        out = ApprovalRequest.from_dict(d)
        assert out.status == ApprovalStatus.APPROVED

    def test_notify_falsy_send(self, tmp_path: Path) -> None:
        from runtime.approval_service import ApprovalRequest, ApprovalService, ApprovalStatus

        svc = ApprovalService.__new__(ApprovalService)
        ch = MagicMock()
        ch.name = "noop"
        ch.send.return_value = False
        svc._channels = [cast(Any, ch)]
        req = ApprovalRequest(
            id="r", action="a", args={}, reason="r",
            status=ApprovalStatus.PENDING,
        )
        assert svc.notify(req) == []


class TestLayersResidual:
    def test_enforce_no_violation(self) -> None:
        from runtime.layers import enforce_import_layering

        # aizee_cli (CLI, L6) may depend on runtime (RUNTIME, L2)
        enforce_import_layering(Path("proj/aizee_cli/x.py"), "runtime.kernel")

    def test_package_key_at_path_end(self) -> None:
        from runtime.layers import _package_for_path

        assert _package_for_path(Path("x/runtime")) == "runtime"


class TestLearningLoopExplicitArgs:
    def test_rank_and_inject_explicit(self) -> None:
        from runtime.learning_loop import LearningLoop, Pattern

        ll = LearningLoop.__new__(LearningLoop)
        p = Pattern(action="a", gate="g", total=3, successes=2, last_seen="t")
        ranked = ll.rank(patterns=[p])
        assert ranked == [p]
        out = ll.inject(ranked=[p])
        assert "Learned Patterns" in out


class TestContractEmitterReraise:
    def test_contract_emit_error_reraised(self, tmp_path: Path) -> None:
        import runtime.contract_emitter as ce

        with patch.object(ce, "emit_contract", side_effect=ce.ContractEmitError("bad")):
            with pytest.raises(ce.ContractEmitError):
                ce.emit_contracts([object], output_dir=tmp_path)


class TestCommandsPending:
    def test_pending_result_continues(self) -> None:
        from runtime.commands import CommandBus, CommandResult, CommandStatus

        bus = CommandBus()
        cmd = MagicMock()
        cmd.execute.return_value = CommandResult(status=CommandStatus.PENDING)
        bus.add(cmd)
        results = bus.execute({})
        assert len(results) == 1


class TestBudgetEscalationConfig:
    def test_explicit_config(self) -> None:
        from runtime.budget_escalation import EscalationConfig, recomputed_budget_flags

        cfg = EscalationConfig()
        out = recomputed_budget_flags(spend=0, limit=10, config=cfg)
        assert out == (False, False)


class TestBudgetAdvancedResidual:
    def test_settled_none_hold_skipped(self) -> None:
        import time

        from runtime.budget_advanced import ReserveHold, ReserveSettleProtocol

        proto = ReserveSettleProtocol()
        hold = ReserveHold(
            hold_id="h1", scope="s", amount=1.0,
            created_at=time.time(), expires_at=time.time() - 1,
            settled=True, settled_amount=None,
        )
        proto._holds["h1"] = hold
        avail = proto.available("s", 100.0)
        assert avail == 100.0


class TestAuditFallbackBlankLines:
    def test_fallback_skips_blank(self, tmp_path: Path) -> None:
        from runtime.audit import AuditLogger

        logger = AuditLogger.__new__(AuditLogger)
        logger.log_file = MagicMock()
        logger.log_file.exists.return_value = True

        def _open(mode="r", **kw):
            if "b" in mode:
                raise OSError("denied")
            import io

            return io.StringIO('{"a":1}\n\n{"b":2}\n')

        logger.log_file.open = _open
        last = logger._last_hash_nolock()
        assert last != "" and last is not None


class TestApprovalChannelsSmallArgs:
    def test_args_under_800(self) -> None:
        from runtime.approval_channels import SlackChannel
        from runtime.approval_service import ApprovalRequest, ApprovalStatus

        req = ApprovalRequest(
            id="r", action="a", args={"k": "v"}, reason="r",
            status=ApprovalStatus.PENDING,
        )
        fields = SlackChannel._build_fields(req)
        assert any("Args" in f.get("text", "") for f in fields)


class TestHybridBm25Miss:
    def test_bm25_row_not_in_candidates(self) -> None:
        from memory.hybrid import HybridSearcher

        hs = HybridSearcher.__new__(HybridSearcher)
        store = MagicMock()
        store._fts_query.return_value = "q"
        hs.memory_store = store
        hs._bm25_rows = lambda q, k, kind, source: [{"id": "fresh", "score": 1.0}]  # type: ignore[list-item]
        candidates: dict = {"other": {}}
        hs._apply_bm25(candidates, "q", 5, None, None)
        # "fresh" not in candidates -> skipped, not added
        assert "fresh" not in candidates


class TestConfigVersionFallback:
    def test_no_version_match(self) -> None:
        import config

        fake_path = MagicMock()
        fake_pyproject = MagicMock()
        fake_pyproject.exists.return_value = True
        fake_pyproject.read_text.return_value = "[project]\nname='x'\n"
        fake_path.resolve.return_value.parent.__truediv__.return_value = fake_pyproject
        with patch.object(config, "Path", return_value=fake_path):
            assert config._version() == "5.16.0"


class TestSeoGraphScalar:
    def test_graph_scalar_falls_through(self) -> None:
        from aizee_mcp.tools.seo_tools import _classify_schema

        out = _classify_schema({"@graph": "weird-string", "@type": "FAQPage"})
        assert out["type"] == "FAQPage"


class TestMemoryToolsSeenIteration:
    def test_seen_id_later_item(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import aizee_mcp.tools.memory_tools as mt

        a = SimpleNamespace(id="A", kind="k", source="s", content="ca")
        b = SimpleNamespace(id="B", kind="k", source="s", content="cb")
        store = MagicMock()
        store.search.return_value = [a, b]
        store.search_vector.return_value = [{"id": "B", "score": 0.9}]
        monkeypatch.setattr(mt, "memory", lambda: store)
        out = json.loads(_call_query_context(mt))
        item_b = [i for i in out if i["id"] == "B"]
        assert item_b and item_b[0].get("vector") is True


def _call_query_context(mt) -> str:
    """Invoke the registered query_context tool."""
    captured: dict = {}

    class FakeTool:
        def __call__(self, fn=None, *a, **k):
            if callable(fn):
                captured[fn.__name__] = fn
                return fn

            def deco(inner):
                captured[inner.__name__] = inner
                return inner

            return deco

    class FakeMCP:
        tool = FakeTool()
        resource = FakeTool()
        prompt = FakeTool()

    mt.register_memory_tools(FakeMCP())
    return captured["query_context"]("q")


class TestSettingsSectionExits:
    def test_dashboard_valid_proxies(self) -> None:
        from runtime.settings import _validate_section

        _validate_section("dashboard", {"trusted_proxies": ["10.0.0.1"]})

    def test_plugins_valid(self) -> None:
        from runtime.settings import _validate_section

        _validate_section("plugins", {"p1": {"enabled": True}})


class TestSpecEngineRemovedDelta:
    def test_removed_delta_validation(self) -> None:
        from runtime.spec.engine import _SpecValidator
        from runtime.spec.models import DeltaType, Requirement
        from runtime.spec_engine import Spec, SpecDelta, SpecPhase

        spec = Spec(id="S", title="t", phase=SpecPhase.SPECIFY)
        spec.requirements = [Requirement(id="R1", description="d")]
        spec.deltas = [
            SpecDelta(delta_type=DeltaType.REMOVED, requirement_id="R1", description=""),
            SpecDelta(delta_type=DeltaType.ADDED, requirement_id="R2", description="new"),
        ]
        errors = _SpecValidator.validate_deltas(spec)
        assert isinstance(errors, list)

    def test_apply_removed_delta(self, tmp_path: Path) -> None:
        from runtime.spec.models import DeltaType, Requirement, SpecDelta
        from runtime.spec_engine import SpecEngine, SpecPhase

        engine = SpecEngine(tmp_path / "specs")
        engine.init_spec("S1", "T")
        spec = engine.load_spec("S1")
        assert spec is not None
        spec.phase = SpecPhase.TASKS
        spec.requirements = [Requirement(id="R1", description="d")]
        spec.deltas = [SpecDelta(delta_type=DeltaType.REMOVED, requirement_id="R1",
                               description="")]
        engine._apply_single_delta(spec, spec.deltas[0])
        assert spec.requirements == []


class TestTaintListScalar:
    def _fn(self):
        from runtime.policy import default_guardrail_registry

        return default_guardrail_registry._guardrails["input"]["taint_flow_check"]

    def test_list_scalar_skipped(self) -> None:
        r = self._fn()({"tool": "write", "args": {"items": [1, 2.5, "text"]}})
        assert r.tripwire_triggered is False
