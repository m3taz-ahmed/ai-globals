"""Tests for runtime/audit_workflow.py — phased durable audit workflow.

Covers: phased durable audit, checkpointing, workflow state machine
transitions, error/edge cases. AAA pattern, one behavior per test.
FAST tier — no MCP, no kernel, no model loading.
"""

from __future__ import annotations

import json
from pathlib import Path

from runtime.audit_workflow import (
    PHASE_ORDER,
    AuditConfig,
    AuditPhase,
    AuditResult,
    AuditWorkflow,
    AuditWorkflowError,
    PhaseResult,
)


class TestAuditPhase:
    def test_phase_order(self) -> None:
        assert PHASE_ORDER == [
            AuditPhase.DISCOVERY,
            AuditPhase.CRAWL,
            AuditPhase.MULTIPAGE,
            AuditPhase.FINALIZE,
        ]

    def test_phase_values(self) -> None:
        assert AuditPhase.DISCOVERY.value == "discovery"
        assert AuditPhase.CRAWL.value == "crawl"
        assert AuditPhase.MULTIPAGE.value == "multipage"
        assert AuditPhase.FINALIZE.value == "finalize"
        assert AuditPhase.FAILED.value == "failed"
        assert AuditPhase.COMPLETED.value == "completed"

    def test_phase_is_str_enum(self) -> None:
        assert isinstance(AuditPhase.DISCOVERY, str)


class TestAuditConfig:
    def test_defaults(self) -> None:
        config = AuditConfig(start_url="https://example.com")
        assert config.max_pages == 50
        assert config.run_lighthouse is False
        assert config.respect_robots_txt is True

    def test_custom_values(self) -> None:
        config = AuditConfig(
            start_url="https://example.com",
            max_pages=100,
            run_lighthouse=True,
            timeout_seconds=30,
            user_agent="custom-bot/2.0",
        )
        assert config.max_pages == 100
        assert config.run_lighthouse is True
        assert config.timeout_seconds == 30
        assert config.user_agent == "custom-bot/2.0"


class TestAuditWorkflow:
    def test_successful_run(self) -> None:
        config = AuditConfig(start_url="https://example.com")
        workflow = AuditWorkflow(config)

        def make_handler(phase: AuditPhase):
            def handler() -> PhaseResult:
                return PhaseResult(phase=phase, success=True, data={"pages": 10})
            return handler

        for phase in PHASE_ORDER:
            workflow.register_phase_handler(phase, make_handler(phase))

        result = workflow.run()
        assert result.is_completed is True
        assert result.failed_phase is None
        assert len(result.phases) == 4
        assert all(p.success for p in result.phases)

    def test_failure_stops_at_failed_phase(self) -> None:
        config = AuditConfig(start_url="https://example.com")
        workflow = AuditWorkflow(config)

        def discovery_handler() -> PhaseResult:
            return PhaseResult(phase=AuditPhase.DISCOVERY, success=True)

        def crawl_handler() -> PhaseResult:
            return PhaseResult(phase=AuditPhase.CRAWL, success=False, error="Connection refused")

        def unused_handler() -> PhaseResult:
            return PhaseResult(phase=AuditPhase.MULTIPAGE, success=True)

        workflow.register_phase_handler(AuditPhase.DISCOVERY, discovery_handler)
        workflow.register_phase_handler(AuditPhase.CRAWL, crawl_handler)
        workflow.register_phase_handler(AuditPhase.MULTIPAGE, unused_handler)
        workflow.register_phase_handler(AuditPhase.FINALIZE, unused_handler)

        result = workflow.run()
        assert result.is_failed is True
        assert result.failed_phase == AuditPhase.CRAWL
        assert len(result.phases) == 2  # Only discovery + crawl ran

    def test_no_handler_registered(self) -> None:
        config = AuditConfig(start_url="https://example.com")
        workflow = AuditWorkflow(config)
        result = workflow.run()
        assert result.is_failed is True
        assert result.failed_phase == AuditPhase.DISCOVERY

    def test_handler_exception_caught_as_failure(self) -> None:
        config = AuditConfig(start_url="https://example.com")
        workflow = AuditWorkflow(config)

        def boom_handler() -> PhaseResult:
            raise RuntimeError("boom")

        def ok_handler() -> PhaseResult:
            return PhaseResult(phase=AuditPhase.CRAWL, success=True)

        workflow.register_phase_handler(AuditPhase.DISCOVERY, boom_handler)
        workflow.register_phase_handler(AuditPhase.CRAWL, ok_handler)

        result = workflow.run()
        assert result.is_failed is True
        assert result.failed_phase == AuditPhase.DISCOVERY
        assert len(result.phases) == 1
        assert "boom" in result.phases[0].error

    def test_resume_after_failure_skips_completed_phases(self) -> None:
        config = AuditConfig(start_url="https://example.com")
        workflow = AuditWorkflow(config)

        call_log: list[AuditPhase] = []

        def discovery_handler() -> PhaseResult:
            call_log.append(AuditPhase.DISCOVERY)
            return PhaseResult(phase=AuditPhase.DISCOVERY, success=True)

        def crawl_handler() -> PhaseResult:
            call_log.append(AuditPhase.CRAWL)
            return PhaseResult(phase=AuditPhase.CRAWL, success=True)

        def multipage_handler() -> PhaseResult:
            call_log.append(AuditPhase.MULTIPAGE)
            return PhaseResult(phase=AuditPhase.MULTIPAGE, success=True)

        def finalize_handler() -> PhaseResult:
            call_log.append(AuditPhase.FINALIZE)
            return PhaseResult(phase=AuditPhase.FINALIZE, success=True)

        workflow.register_phase_handler(AuditPhase.DISCOVERY, discovery_handler)
        workflow.register_phase_handler(AuditPhase.CRAWL, crawl_handler)
        workflow.register_phase_handler(AuditPhase.MULTIPAGE, multipage_handler)
        workflow.register_phase_handler(AuditPhase.FINALIZE, finalize_handler)

        # Simulate a prior run where discovery succeeded
        workflow._result.phases.append(
            PhaseResult(phase=AuditPhase.DISCOVERY, success=True),
        )
        result = workflow.resume()
        assert result.is_completed is True
        assert AuditPhase.DISCOVERY not in call_log
        assert AuditPhase.CRAWL in call_log

    def test_resume_with_no_checkpoint_runs_all(self) -> None:
        config = AuditConfig(start_url="https://example.com")
        workflow = AuditWorkflow(config)

        def make_handler(phase: AuditPhase):
            def handler() -> PhaseResult:
                return PhaseResult(phase=phase, success=True)
            return handler

        for phase in PHASE_ORDER:
            workflow.register_phase_handler(phase, make_handler(phase))

        result = workflow.resume()
        assert result.is_completed is True
        assert len(result.phases) == 4

    def test_resume_stops_on_failure(self) -> None:
        config = AuditConfig(start_url="https://example.com")
        workflow = AuditWorkflow(config)

        def crawl_fail() -> PhaseResult:
            return PhaseResult(phase=AuditPhase.CRAWL, success=False, error="fail")

        def ok() -> PhaseResult:
            return PhaseResult(phase=AuditPhase.MULTIPAGE, success=True)

        workflow.register_phase_handler(AuditPhase.DISCOVERY, ok)
        workflow.register_phase_handler(AuditPhase.CRAWL, crawl_fail)
        workflow.register_phase_handler(AuditPhase.MULTIPAGE, ok)
        workflow.register_phase_handler(AuditPhase.FINALIZE, ok)

        result = workflow.resume()
        assert result.is_failed is True
        assert result.failed_phase == AuditPhase.CRAWL

    def test_checkpoint_save_and_load(self, tmp_path: Path) -> None:
        config = AuditConfig(start_url="https://example.com")
        workflow = AuditWorkflow(config, checkpoint_dir=tmp_path)

        def handler() -> PhaseResult:
            return PhaseResult(phase=AuditPhase.DISCOVERY, success=True)
        workflow.register_phase_handler(AuditPhase.DISCOVERY, handler)

        # Run just discovery
        workflow._result.current_phase = AuditPhase.DISCOVERY
        phase_result = workflow._execute_phase(AuditPhase.DISCOVERY)
        workflow._result.phases.append(phase_result)
        workflow._save_checkpoint()

        # Check file exists
        checkpoint = tmp_path / f"audit_{workflow.audit_id}.json"
        assert checkpoint.exists()

    def test_checkpoint_persisted_during_full_run(self, tmp_path: Path) -> None:
        config = AuditConfig(start_url="https://example.com")
        workflow = AuditWorkflow(config, checkpoint_dir=tmp_path)

        def make_handler(phase: AuditPhase):
            def handler() -> PhaseResult:
                return PhaseResult(phase=phase, success=True)
            return handler

        for phase in PHASE_ORDER:
            workflow.register_phase_handler(phase, make_handler(phase))

        workflow.run()
        checkpoint = tmp_path / f"audit_{workflow.audit_id}.json"
        assert checkpoint.exists()
        data = json.loads(checkpoint.read_text(encoding="utf-8"))
        assert data["is_completed"] is True
        assert len(data["phases"]) == 4

    def test_checkpoint_load_reconstructs_result(self, tmp_path: Path) -> None:
        config = AuditConfig(start_url="https://example.com")
        workflow = AuditWorkflow(config, checkpoint_dir=tmp_path)

        def make_handler(phase: AuditPhase):
            def handler() -> PhaseResult:
                return PhaseResult(phase=phase, success=True)
            return handler

        for phase in PHASE_ORDER:
            workflow.register_phase_handler(phase, make_handler(phase))

        workflow.run()
        loaded = workflow._load_checkpoint()
        assert loaded is not None
        assert loaded.is_completed is True
        assert len(loaded.phases) == 4

    def test_no_checkpoint_dir_skips_save(self, tmp_path: Path) -> None:
        config = AuditConfig(start_url="https://example.com")
        workflow = AuditWorkflow(config)

        def handler() -> PhaseResult:
            return PhaseResult(phase=AuditPhase.DISCOVERY, success=True)
        workflow.register_phase_handler(AuditPhase.DISCOVERY, handler)

        workflow._save_checkpoint()
        # No file should be created
        assert workflow._checkpoint_path() is None

    def test_load_checkpoint_missing_returns_none(self, tmp_path: Path) -> None:
        config = AuditConfig(start_url="https://example.com")
        workflow = AuditWorkflow(config, checkpoint_dir=tmp_path)
        assert workflow._load_checkpoint() is None

    def test_get_progress(self) -> None:
        config = AuditConfig(start_url="https://example.com")
        workflow = AuditWorkflow(config)

        def handler() -> PhaseResult:
            return PhaseResult(phase=AuditPhase.DISCOVERY, success=True)
        workflow.register_phase_handler(AuditPhase.DISCOVERY, handler)

        workflow._result.current_phase = AuditPhase.DISCOVERY
        workflow._result.phases.append(
            PhaseResult(phase=AuditPhase.DISCOVERY, success=True),
        )

        progress = workflow.get_progress()
        assert progress["phases_completed"] == 1
        assert progress["phases_total"] == 4
        assert progress["progress_pct"] == 25

    def test_get_progress_all_completed(self) -> None:
        config = AuditConfig(start_url="https://example.com")
        workflow = AuditWorkflow(config)

        for phase in PHASE_ORDER:
            workflow._result.phases.append(
                PhaseResult(phase=phase, success=True),
            )
        workflow._result.current_phase = AuditPhase.COMPLETED

        progress = workflow.get_progress()
        assert progress["phases_completed"] == 4
        assert progress["progress_pct"] == 100
        assert progress["is_completed"] is True

    def test_get_progress_zero_when_no_phases(self) -> None:
        config = AuditConfig(start_url="https://example.com")
        workflow = AuditWorkflow(config)
        progress = workflow.get_progress()
        assert progress["phases_completed"] == 0
        assert progress["progress_pct"] == 0

    def test_register_phase_handler_overwrites(self) -> None:
        config = AuditConfig(start_url="https://example.com")
        workflow = AuditWorkflow(config)

        def handler1() -> PhaseResult:
            return PhaseResult(phase=AuditPhase.DISCOVERY, success=True)

        def handler2() -> PhaseResult:
            return PhaseResult(phase=AuditPhase.DISCOVERY, success=False, error="x")

        workflow.register_phase_handler(AuditPhase.DISCOVERY, handler1)
        workflow.register_phase_handler(AuditPhase.DISCOVERY, handler2)

        result = workflow.run()
        assert result.is_failed is True
        assert result.phases[0].success is False

    def test_phase_result_has_duration(self) -> None:
        config = AuditConfig(start_url="https://example.com")
        workflow = AuditWorkflow(config)

        def slow_handler() -> PhaseResult:
            return PhaseResult(phase=AuditPhase.DISCOVERY, success=True)

        workflow.register_phase_handler(AuditPhase.DISCOVERY, slow_handler)
        pr = workflow._execute_phase(AuditPhase.DISCOVERY)
        assert pr.duration_ms >= 0.0


class TestAuditResult:
    def test_to_dict(self) -> None:
        result = AuditResult(
            audit_id="test-123",
            config=AuditConfig(start_url="https://example.com"),
        )
        result.phases.append(PhaseResult(phase=AuditPhase.DISCOVERY, success=True))
        d = result.to_dict()
        assert d["audit_id"] == "test-123"
        assert d["current_phase"] == "discovery"
        assert len(d["phases"]) == 1

    def test_to_dict_with_failed_phase(self) -> None:
        result = AuditResult(
            audit_id="test-456",
            config=AuditConfig(start_url="https://example.com"),
            current_phase=AuditPhase.FAILED,
            failed_phase=AuditPhase.CRAWL,
        )
        d = result.to_dict()
        assert d["is_failed"] is True
        assert d["failed_phase"] == "crawl"

    def test_is_completed_property(self) -> None:
        result = AuditResult(
            audit_id="x",
            config=AuditConfig(start_url="https://example.com"),
            current_phase=AuditPhase.COMPLETED,
        )
        assert result.is_completed is True
        assert result.is_failed is False

    def test_is_failed_property(self) -> None:
        result = AuditResult(
            audit_id="x",
            config=AuditConfig(start_url="https://example.com"),
            current_phase=AuditPhase.FAILED,
        )
        assert result.is_failed is True
        assert result.is_completed is False

    def test_duration_ms_when_completed(self) -> None:
        result = AuditResult(
            audit_id="x",
            config=AuditConfig(start_url="https://example.com"),
            started_at=100.0,
            completed_at=100.5,
        )
        assert result.duration_ms == 500.0

    def test_duration_ms_zero_when_not_completed(self) -> None:
        result = AuditResult(
            audit_id="x",
            config=AuditConfig(start_url="https://example.com"),
        )
        assert result.duration_ms == 0.0

    def test_to_dict_includes_phase_errors(self) -> None:
        result = AuditResult(
            audit_id="x",
            config=AuditConfig(start_url="https://example.com"),
        )
        result.phases.append(
            PhaseResult(
                phase=AuditPhase.CRAWL, success=False, error="timeout",
            ),
        )
        d = result.to_dict()
        assert d["phases"][0]["error"] == "timeout"
        assert d["phases"][0]["success"] is False


class TestAuditWorkflowError:
    def test_error_carries_phase_context(self) -> None:
        err = AuditWorkflowError("boom", phase=AuditPhase.CRAWL)
        assert err.error_code == "AUDIT_WORKFLOW_ERROR"
        assert err.context["phase"] == "crawl"

    def test_error_without_phase(self) -> None:
        err = AuditWorkflowError("boom")
        assert err.context == {}
        assert "boom" in str(err)
