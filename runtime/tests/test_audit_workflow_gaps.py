"""Gap tests for runtime/audit_workflow.py — checkpoint resume paths."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from runtime.audit_workflow import (
    AuditConfig,
    AuditPhase,
    AuditWorkflow,
    PhaseResult,
)


def _wf(tmp_path) -> AuditWorkflow:
    return AuditWorkflow(AuditConfig(start_url="https://x.test"), checkpoint_dir=tmp_path)


def _ok(phase: AuditPhase) -> PhaseResult:
    return PhaseResult(phase=phase, success=True)


class TestResume:
    def test_resume_uses_saved_checkpoint(self, tmp_path):
        wf = _wf(tmp_path)
        for ph in (AuditPhase.DISCOVERY, AuditPhase.CRAWL,
                   AuditPhase.MULTIPAGE, AuditPhase.FINALIZE):
            wf.register_phase_handler(ph, lambda ph=ph: _ok(ph))
        wf.run()
        # second workflow resumes from checkpoint (line 208)
        wf2 = _wf(tmp_path)
        wf2.audit_id = wf.audit_id  # same checkpoint file
        for ph in (AuditPhase.DISCOVERY, AuditPhase.CRAWL,
                   AuditPhase.MULTIPAGE, AuditPhase.FINALIZE):
            wf2.register_phase_handler(ph, lambda ph=ph: _ok(ph))
        res = wf2.resume()
        assert res.current_phase == AuditPhase.COMPLETED

    def test_resume_reruns_failed_phase(self, tmp_path):
        wf = _wf(tmp_path)
        wf.register_phase_handler(AuditPhase.DISCOVERY, lambda: _ok(AuditPhase.DISCOVERY))
        calls = []
        def bad():
            calls.append(1)
            return PhaseResult(phase=AuditPhase.CRAWL, success=False, error="boom")
        wf.register_phase_handler(AuditPhase.CRAWL, bad)
        wf.run()
        wf.register_phase_handler(AuditPhase.CRAWL, lambda: _ok(AuditPhase.CRAWL))
        wf.register_phase_handler(AuditPhase.MULTIPAGE, lambda: _ok(AuditPhase.MULTIPAGE))
        wf.register_phase_handler(AuditPhase.FINALIZE, lambda: _ok(AuditPhase.FINALIZE))
        res = wf.resume()
        assert res.is_completed
        assert calls  # bad handler ran once

    def test_resume_still_fails(self, tmp_path):
        wf = _wf(tmp_path)
        for ph in (AuditPhase.DISCOVERY, AuditPhase.CRAWL,
                   AuditPhase.MULTIPAGE, AuditPhase.FINALIZE):
            wf.register_phase_handler(ph, lambda ph=ph: PhaseResult(phase=ph, success=False))
        res = wf.resume()
        assert res.is_failed


class TestCheckpointIO:
    def test_save_oserror(self, tmp_path):
        wf = _wf(tmp_path)
        with patch.object(Path, "write_text", side_effect=OSError("disk full")):
            wf._save_checkpoint()  # warns, no raise

    def test_load_bad_json(self, tmp_path):
        wf = _wf(tmp_path)
        p = wf._checkpoint_path()
        p.write_text("{nope", encoding="utf-8")
        assert wf._load_checkpoint() is None

    def test_load_bad_current_phase(self, tmp_path):
        wf = _wf(tmp_path)
        p = wf._checkpoint_path()
        p.write_text(json.dumps({
            "audit_id": wf.audit_id, "current_phase": "bogus_phase",
            "phases": [],
        }), encoding="utf-8")
        res = wf._load_checkpoint()
        assert res is not None and res.current_phase == AuditPhase.DISCOVERY

    def test_load_bad_failed_phase_and_phase_entries(self, tmp_path):
        wf = _wf(tmp_path)
        p = wf._checkpoint_path()
        p.write_text(json.dumps({
            "audit_id": wf.audit_id,
            "current_phase": "crawl",
            "failed_phase": "nope_phase",
            "phases": [
                {"phase": "badphase", "success": True},
                {"phase": "discovery", "success": True, "duration_ms": 5},
            ],
        }), encoding="utf-8")
        res = wf._load_checkpoint()
        assert res is not None
        assert res.failed_phase is None  # bad value ignored
        assert len(res.phases) == 1

    def test_load_missing(self, tmp_path):
        wf = _wf(tmp_path)
        assert wf._load_checkpoint() is None

    def test_no_checkpoint_dir(self):
        wf = AuditWorkflow(AuditConfig(start_url="https://x.test"))
        assert wf._checkpoint_path() is None
        wf._save_checkpoint()
        assert wf._load_checkpoint() is None

    def test_execute_phase_no_handler(self, tmp_path):
        wf = _wf(tmp_path)
        res = wf._execute_phase(AuditPhase.DISCOVERY)
        assert res.success is False
        assert "No handler" in res.error

    def test_execute_phase_raises(self, tmp_path):
        wf = _wf(tmp_path)
        wf.register_phase_handler(AuditPhase.DISCOVERY, lambda: 1 / 0)
        res = wf._execute_phase(AuditPhase.DISCOVERY)
        assert res.success is False
        assert "division" in res.error
