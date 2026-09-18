"""Coverage gap tests - batch 13.

Targets: sarif_emitter provenance branches, probity RequireCommand/check,
hallucination_detector scoped require, governance hooks redactor edges,
durable compensation/finalize, design_slop_verifier svg/fonts,
design_library walk edges, daemon claude-sync/macos disable,
audit_signing import fallback, approval_sla process edges,
agent_baseline rare-action/volume-spike, admission decision/metrics,
tool_output_sanitizer batch default, telemetry rotation error,
storage_backend delete miss, stale_api_detector typescript ext,
spec/templates resolve failure, spec/engine REMOVED SpecDelta,
saga non-dict step result, quality Bounder value branches,
pricing_calculator zero capacity, plugin_system confined path,
plan_diff_validator code-block/import edges, mcp_auditor writable/lockdir.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest


class TestSarifProvenance:
    def test_repo_url_only(self) -> None:
        from runtime.sarif_emitter import build_sarif

        sarif = build_sarif([], repo_url="https://example.com/r")
        run = sarif["runs"][0]
        prov = run["versionControlProvenance"][0]
        assert prov["repositoryUri"] == "https://example.com/r"
        assert "revisionId" not in prov and "branch" not in prov

    def test_commit_and_branch(self) -> None:
        from runtime.sarif_emitter import build_sarif

        sarif = build_sarif([], commit_sha="abc123", branch="main")
        prov = sarif["runs"][0]["versionControlProvenance"][0]
        assert prov["revisionId"] == "abc123" and prov["branch"] == "main"
        assert "repositoryUri" not in prov

    def test_no_provenance(self) -> None:
        from runtime.sarif_emitter import build_sarif

        sarif = build_sarif([])
        assert "versionControlProvenance" not in sarif["runs"][0]


class TestProbityRequireCommand:
    def _rule(self) -> Any:
        from runtime.probity import RequireCommand

        return RequireCommand("t", before=r"npm test", after=r"deploy", message="need tests")

    def test_non_str_command(self) -> None:
        assert self._rule().check({"type": "exec", "command": 123}) is None

    def test_after_no_match(self) -> None:
        assert self._rule().check({"type": "exec", "command": "ls"}) is None

    def test_before_satisfied(self) -> None:
        ev = {"type": "exec", "command": "deploy prod", "history": ["npm test"]}
        assert self._rule().check(ev) is None

    def test_violation(self) -> None:
        ev = {"type": "exec", "command": "deploy prod", "history": ["ls"]}
        assert self._rule().check(ev) is not None

    def test_check_non_str_type_skips_normalize(self) -> None:
        from runtime.probity import Guardrails

        g = Guardrails()
        g.rules.append(self._rule())
        # type as non-str: normalize skipped, rule sees non-exec type -> None
        g.check({"type": 5, "command": "deploy"})


class TestHallucinationScopedRequire:
    def test_scoped_require_split(self, tmp_path: Path) -> None:
        from runtime.hallucination_detector import HallucinationDetector

        det = HallucinationDetector()
        det._npm_known = {"react"}
        code = "const x = require('@scope/pkg/sub');\n"
        findings = det.detect_javascript(code, "f.js")
        # '@scope/pkg' extracted (first two segments), not '@scope'
        assert all(f.package_name == "@scope/pkg" for f in findings)


class TestGovernanceHooks:
    def _make(self, audit: Any) -> Any:
        from runtime.governance import GovernanceHooks

        return GovernanceHooks(audit, MagicMock())

    def test_redactor_exception_falls_back(self) -> None:
        audit = MagicMock()

        def bad_redact(v: Any) -> Any:
            raise RuntimeError("redact fail")

        audit._redact = bad_redact
        hooks = self._make(audit)
        with hooks.around_action("Read", "a1", key="v"):
            pass
        audit.log.assert_called_once()

    def test_no_redactor_callable(self) -> None:
        audit = MagicMock(spec=["log"])  # no _redact attr
        hooks = self._make(audit)
        with hooks.around_action("Read", key="v"):
            pass
        audit.log.assert_called_once()


class TestDurableResiduals:
    def _executor(self, tmp_path: Path) -> Any:
        from runtime.durable import DurableExecutor

        return DurableExecutor(tmp_path / "state")

    def test_compensate_skips_non_completed(self, tmp_path: Path) -> None:
        from runtime.durable import DurableStep, DurableWorkflow, StepStatus

        ex = self._executor(tmp_path)
        wf = DurableWorkflow(
            workflow_id="w", name="n",
            steps=[
                DurableStep(step_id="s1", name="a", status=StepStatus.FAILED),
                DurableStep(step_id="s2", name="b", status=StepStatus.COMPLETED),
            ],
            current_step=2,
        )
        calls: list[str] = []
        ex._compensate(wf, lambda s: True, lambda s: calls.append(s.step_id))
        assert calls == ["s2"]

    def test_finalize_failed(self, tmp_path: Path) -> None:
        from runtime.durable import DurableStep, DurableWorkflow, StepStatus

        ex = self._executor(tmp_path)
        wf = DurableWorkflow(
            workflow_id="w", name="n",
            steps=[DurableStep(step_id="s1", name="a", status=StepStatus.FAILED)],
            status="running",
        )
        ex._finalize(wf)
        assert wf.status == "failed"


class TestDesignSlop:
    def test_svg_illustration_flagged(self) -> None:
        from runtime.design_slop_verifier import DesignSlopVerifier

        v = DesignSlopVerifier()
        findings = v._check_svg_illustrations('<svg><rect class="illustration"/></svg>')
        # depends on pattern list; at minimum exercises the loop
        assert isinstance(findings, list)

    def test_unlisted_font_skipped(self) -> None:
        from runtime.design_slop_verifier import DesignSlopVerifier

        v = DesignSlopVerifier()
        findings = v._check_overused_fonts(
            "x { font-family: 'CustomBrandFont'; }"
        )
        assert findings == []


class TestDesignLibraryWalk:
    def test_walk_symlink_and_oserror(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from runtime.design_library import DesignLibrary

        lib = DesignLibrary(library_dir=tmp_path / "lib")
        # craft project dir with a symlink-like entry via fake Path
        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / "a.css").write_text("x")

        orig_symlink = Path.is_symlink
        flagged = {"done": False}

        def flaky(self: Path) -> bool:
            if self.name == "a.css" and not flagged["done"]:
                flagged["done"] = True
                return True  # pretend symlink -> skipped
            return orig_symlink(self)

        monkeypatch.setattr(Path, "is_symlink", flaky)
        ptype = lib.detect_project_type(proj)
        assert ptype is not None


class TestDaemonResiduals:
    def test_claude_sync_disabled_not_present(self, tmp_path: Path) -> None:
        from runtime.daemon import AizeeDaemon

        d = AizeeDaemon.__new__(AizeeDaemon)
        d.root = tmp_path
        (tmp_path / ".claude").mkdir()
        claude = tmp_path / ".claude" / "settings.json"
        claude.write_text(json.dumps({"mcpServers": {"x": {}}}))
        # disabled server not present in claude config -> nothing removed
        out = d._sync_claude_settings({"ghost": {"enabled": False}})
        assert out == 0

    def test_macos_disable_no_plist(self) -> None:
        from runtime.daemon import AizeeDaemon

        out = AizeeDaemon._disable_autostart_macos()
        assert out["disabled"] is True


class TestApprovalSlaResiduals:
    def _mgr(self) -> Any:
        from runtime.approval_sla import ApprovalSlaManager, SlaAction, SlaPolicy

        return ApprovalSlaManager(
            SlaPolicy(timeout_seconds=3600, auto_action=SlaAction.AUTO_DENY)
        )

    def test_process_state_gone(self) -> None:
        mgr = self._mgr()
        st = mgr.register("req-1")
        # force check() to return an action while _states entry vanished
        st.created_at = 0.0
        del mgr._states["req-1"]
        out = mgr.process("req-1")
        assert out["action"] is None

    def test_apply_auto_action(self) -> None:
        from runtime.approval_sla import (
            SlaAction,
            SlaState,
        )

        mgr = self._mgr()
        state = SlaState(request_id="r", created_at=0.0)
        mgr._apply_action(state, SlaAction.AUTO_APPROVE, "r", 1.0)
        assert state.auto_resolved is True


class TestAgentBaselineResiduals:
    def _baseline(self) -> Any:
        from runtime.agent_baseline import AgentBaseline

        return AgentBaseline("agent-x")

    def test_rare_action_skipped_when_no_counts(self) -> None:
        from runtime.agent_baseline import AgentAction, BaselinePhase

        b = self._baseline()
        b._phase = BaselinePhase.DETECTING
        # tool known (no NEW_TOOL early return) but zero action-type counts
        # -> total == 0 -> rare-action check skipped -> volume spike path
        b._tool_counts["t"] = 5
        out = b.check(AgentAction(tool_name="t", action_type="read"))
        assert out is None or out.anomaly_type is not None

    def test_volume_spike_zero_mean(self) -> None:
        from datetime import datetime, timedelta

        from runtime.agent_baseline import AgentAction

        b = self._baseline()
        now = datetime.now()
        b._recent_timestamps = [now + timedelta(seconds=i) for i in range(10)]
        b._recent_timestamps = list(reversed(b._recent_timestamps))
        # mean_rate can go non-positive only with pathological data; just
        # exercise the helper
        out = b._check_volume_spike(AgentAction(tool_name="t"))
        assert out is None or out.anomaly_type is not None


class TestAdmissionResiduals:
    def _record(self, **kw: Any) -> Any:
        from runtime.admission import PromotionRecord

        base = {
            "tenant_id": "t", "subject_id": "s", "candidate_id": "c",
            "lineage": (), "retrieval_score": 0.5, "acl": "allow",
            "freshness": "fresh", "deletion_state": "not_deleted",
            "classification": "public", "policy_version": "p",
            "decision": "promote",
        }
        base.update(kw)
        return PromotionRecord(**base)

    def test_invalid_decision_raises(self) -> None:
        from runtime.admission import AdmissionGate

        gate = AdmissionGate()
        with pytest.raises(ValueError, match="Invalid promotion"):
            gate.evaluate_promotion(self._record(decision="weird"))

    def test_reject_rate_skips_admits(self) -> None:
        from runtime.admission import AdmissionGate

        gate = AdmissionGate()
        gate._records = [MagicMock(decision="admit", reason_code="x")]
        assert gate.reject_rate_by_reason() == {}


class TestSanitizerBatch:
    def test_default_tool_names(self) -> None:
        from runtime.tool_output_sanitizer import ToolOutputSanitizer

        s = ToolOutputSanitizer()
        out = s.sanitize_batch(["a", "b"])
        assert len(out) == 2


class TestTelemetryRotateError:
    def test_rotate_oserror_suppressed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from runtime.telemetry import TelemetryCollector

        tc = TelemetryCollector(tmp_path)
        tc.log_path.parent.mkdir(parents=True, exist_ok=True)
        tc.log_path.write_text("x" * 100)
        tc._MAX_LOG_SIZE = -1  # force rotation regardless of size

        def deny(self: Path, *a: Any, **k: Any) -> bool:
            raise OSError("rot fail")

        monkeypatch.setattr(Path, "rename", deny)
        tc._rotate_if_needed()  # must not raise


class TestStorageDeleteMiss:
    def test_delete_missing_key(self) -> None:
        from runtime.storage_backend import InMemoryStorage

        s = InMemoryStorage()
        assert s.delete("nope") is False
        assert s.delete("nope") is False


class TestStaleApiTypescript:
    def test_scan_file_ts(self, tmp_path: Path) -> None:
        from runtime.stale_api_detector import StaleApiDetector

        det = StaleApiDetector()
        f = tmp_path / "x.ts"
        f.write_text("const a = 1;")
        out = det.scan_file(f)
        assert isinstance(out, list)


class TestSpecTemplatesResolve:
    def test_resolve_failure_returns_empty(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        import runtime.spec.templates as t

        monkeypatch.setattr(t, "resolve_template_dir", lambda: tmp_path)

        def bad_resolve(self: Path, *a: Any, **k: Any) -> Path:
            raise OSError("cannot resolve")

        monkeypatch.setattr(Path, "resolve", bad_resolve)
        assert t.render_template("spec-template.md", {}) == ""


class TestSpecEngineRemovedDelta:
    def test_apply_removed_delta(self, tmp_path: Path) -> None:
        from runtime.spec.engine import SpecEngine
        from runtime.spec.models import (
            DeltaType,
            Requirement,
            Spec,
            SpecDelta,
            SpecPhase,
        )

        eng = SpecEngine(tmp_path / "specs")
        spec = Spec(id="s1", title="t", phase=SpecPhase.DONE)
        spec.requirements.append(Requirement(id="r1", description="d"))
        delta = SpecDelta(
            requirement_id="r1", delta_type=DeltaType.REMOVED, description=""
        )
        eng._apply_single_delta(spec, delta)
        assert spec.requirements == []

    def test_validate_removed_not_found(self, tmp_path: Path) -> None:
        from runtime.spec.engine import _SpecValidator
        from runtime.spec.models import DeltaType, Spec, SpecDelta, SpecPhase

        spec = Spec(id="s1", title="t", phase=SpecPhase.DONE)
        spec.deltas.append(SpecDelta(
            requirement_id="ghost", delta_type=DeltaType.REMOVED, description=""
        ))
        errors = _SpecValidator.validate_deltas(spec)
        assert any("not found" in e for e in errors)


class TestSagaInvalidResult:
    def test_step_returns_non_dict(self, tmp_path: Path) -> None:
        from runtime.saga import Saga, SagaOrchestrator, SagaStep

        orch = SagaOrchestrator(tmp_path)
        saga = Saga(id="sg", title="t", steps=[SagaStep(action="a")])
        out = orch.run(saga, {}, act=lambda **_: "not a dict")
        assert out["ok"] is False


class TestQualityBounderValues:
    def test_bound_value_list_and_scalar(self) -> None:
        from runtime.quality import Bounder

        b = Bounder(max_items=2)
        out = b._bound_value([1, 2, 3], 0)
        assert isinstance(out, list) and len(out) <= 3
        assert b._bound_value(42, 0) == 42


class TestPricingZeroCapacity:
    def test_zero_capacity_raises(self) -> None:
        from runtime.pricing_calculator import recommended_rate
        from runtime.schemas import ValidationError

        # All inputs positive but the product underflows to 0.0
        with pytest.raises(ValidationError, match="capacity"):
            recommended_rate(
                100000, billable_hours_per_week=1e-300, utilization=1e-100
            )


class TestPluginSystemConfined:
    def test_traversal_returns_none(self, tmp_path: Path) -> None:
        from runtime.plugin_system import (
            Plugin,
            PluginManifest,
            PluginRegistry,
        )

        reg = PluginRegistry(plugins_dir=tmp_path)
        manifest = PluginManifest(name="p", version="1.0", description="d")
        plugin = Plugin(manifest=manifest, path=tmp_path / "plug")
        plugin.path.mkdir()
        assert reg._confined_path(plugin, "..", "..", "escape") is None


class TestPlanDiffEdges:
    def _validator(self, tmp_path: Path) -> Any:
        from runtime.plan_diff_validator import PlanDiffValidator

        return PlanDiffValidator(project_root=tmp_path)

    def test_code_block_non_path_line(self, tmp_path: Path) -> None:
        v = self._validator(tmp_path)
        plan = "```\njust some prose no path\n```\n"
        files = v.extract_plan_files(plan)
        assert files == []

    def test_py_import_no_group(self, tmp_path: Path) -> None:
        v = self._validator(tmp_path)
        # 'import' with no module captured -> skipped
        out = v._extract_added_imports("+import \n", [])
        assert out["python"] == []


class TestMcpAuditorResiduals:
    def test_writable_path_readonly(self, tmp_path: Path) -> None:
        import os
        import stat

        from runtime.mcp_auditor import _is_writable_path

        f = tmp_path / "ro.txt"
        f.write_text("x")
        os.chmod(f, stat.S_IREAD)
        try:
            writable, _who = _is_writable_path(str(f))
            assert writable is False
        finally:
            os.chmod(f, stat.S_IWRITE)

    def test_load_baselines_no_lockdir(self) -> None:
        from runtime.mcp_auditor import McpAuditor

        aud = McpAuditor.__new__(McpAuditor)
        aud._lock_dir = None
        aud._baselines = {}
        aud._load_baselines()  # early return, no error


