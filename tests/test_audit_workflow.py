"""Tests for runtime/audit_workflow.py — phased durable audit workflow.

FAST tier — no MCP, no kernel, no model loading.
"""

from __future__ import annotations

from pathlib import Path

from runtime.audit_workflow import (
    PHASE_ORDER,
    AuditConfig,
    AuditPhase,
    AuditResult,
    AuditWorkflow,
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


class TestAuditConfig:
    def test_defaults(self) -> None:
        config = AuditConfig(start_url="https://example.com")
        assert config.max_pages == 50
        assert config.run_lighthouse is False
        assert config.respect_robots_txt is True


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
