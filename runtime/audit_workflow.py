"""Phased durable audit workflow engine.

Ported from open-seo (every-app/open-seo)
``src/server/workflows/SiteAuditWorkflow.ts`` + ``siteAuditWorkflowPhases.ts``.
Provides a phased audit pipeline with checkpointing: each phase runs
independently, failed phases don't redo completed ones, and phase
state is persisted for resumption.

Phases (in order):
1. ``DISCOVERY`` — fetch robots.txt, parse sitemap.xml, build URL frontier
2. ``CRAWL`` — fetch each URL, parse HTML, extract SEO data
3. ``MULTIPAGE`` — run cross-page checks (duplicates, chains, orphans)
4. ``FINALIZE`` — aggregate issues, compute health score, emit report

Usage::

    from runtime.audit_workflow import AuditWorkflow, AuditConfig
    workflow = AuditWorkflow(config=AuditConfig(start_url="https://example.com"))
    result = workflow.run()
    if result.failed_phase:
        # Resume from checkpoint
        result = workflow.resume()
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from runtime.schemas import AizeeError, ErrorSeverity

_logger = logging.getLogger(__name__)


class AuditPhase(str, Enum):
    """Phases of the audit workflow, in execution order."""

    DISCOVERY = "discovery"
    CRAWL = "crawl"
    MULTIPAGE = "multipage"
    FINALIZE = "finalize"
    FAILED = "failed"
    COMPLETED = "completed"


PHASE_ORDER: list[AuditPhase] = [
    AuditPhase.DISCOVERY,
    AuditPhase.CRAWL,
    AuditPhase.MULTIPAGE,
    AuditPhase.FINALIZE,
]


@dataclass
class AuditConfig:
    """Configuration for an audit run."""

    start_url: str
    max_pages: int = 50
    run_lighthouse: bool = False
    user_agent: str = "aizee-audit-bot/1.0"
    timeout_seconds: int = 15
    respect_robots_txt: bool = True
    max_sitemap_depth: int = 3
    max_sitemap_docs: int = 300
    max_robots_bytes: int = 500 * 1024
    max_sitemap_bytes: int = 10 * 1024 * 1024


@dataclass
class PhaseResult:
    """Result of one phase execution."""

    phase: AuditPhase
    success: bool
    duration_ms: float = 0.0
    data: dict[str, Any] = field(default_factory=dict)
    error: str = ""


@dataclass
class AuditResult:
    """Aggregate result of an audit run."""

    audit_id: str
    config: AuditConfig
    phases: list[PhaseResult] = field(default_factory=list)
    current_phase: AuditPhase = AuditPhase.DISCOVERY
    failed_phase: AuditPhase | None = None
    pages_crawled: int = 0
    issues: list[dict[str, Any]] = field(default_factory=list)
    health_score: int = 100
    started_at: float = 0.0
    completed_at: float = 0.0

    @property
    def is_completed(self) -> bool:
        return self.current_phase == AuditPhase.COMPLETED

    @property
    def is_failed(self) -> bool:
        return self.current_phase == AuditPhase.FAILED

    @property
    def duration_ms(self) -> float:
        if self.completed_at > 0:
            return (self.completed_at - self.started_at) * 1000
        return 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "audit_id": self.audit_id,
            "current_phase": self.current_phase.value,
            "failed_phase": self.failed_phase.value if self.failed_phase else None,
            "pages_crawled": self.pages_crawled,
            "issue_count": len(self.issues),
            "health_score": self.health_score,
            "is_completed": self.is_completed,
            "is_failed": self.is_failed,
            "duration_ms": round(self.duration_ms, 2),
            "phases": [
                {
                    "phase": p.phase.value,
                    "success": p.success,
                    "duration_ms": round(p.duration_ms, 2),
                    "error": p.error,
                }
                for p in self.phases
            ],
        }


class AuditWorkflowError(AizeeError):
    """Raised when the audit workflow encounters an unrecoverable error."""

    def __init__(self, message: str, phase: AuditPhase | None = None) -> None:
        context: dict[str, Any] = {}
        if phase:
            context["phase"] = phase.value
        super().__init__(
            "AUDIT_WORKFLOW_ERROR", message, ErrorSeverity.HIGH, context,
        )


class AuditWorkflow:
    """Phased audit workflow with checkpointing.

    Each phase runs independently. If a phase fails, the workflow
    stops and can be resumed from the last successful phase.
    """

    def __init__(
        self,
        config: AuditConfig,
        checkpoint_dir: Path | None = None,
    ) -> None:
        import uuid

        self.config = config
        self.audit_id = str(uuid.uuid4())
        self._checkpoint_dir = checkpoint_dir
        self._result = AuditResult(
            audit_id=self.audit_id,
            config=config,
            started_at=time.time(),
        )
        self._phase_handlers: dict[AuditPhase, Callable[[], PhaseResult]] = {}

    def register_phase_handler(
        self,
        phase: AuditPhase,
        handler: Callable[[], PhaseResult],
    ) -> None:
        """Register a callable that executes *phase* and returns a PhaseResult."""
        self._phase_handlers[phase] = handler

    def run(self) -> AuditResult:
        """Run all phases in order. Stops on first failure."""
        self._result.started_at = time.time()
        for phase in PHASE_ORDER:
            self._result.current_phase = phase
            phase_result = self._execute_phase(phase)
            self._result.phases.append(phase_result)
            self._save_checkpoint()
            if not phase_result.success:
                self._result.failed_phase = phase
                self._result.current_phase = AuditPhase.FAILED
                return self._result
        self._result.current_phase = AuditPhase.COMPLETED
        self._result.completed_at = time.time()
        self._save_checkpoint()
        return self._result

    def resume(self) -> AuditResult:
        """Resume from the last checkpoint after a failure."""
        saved = self._load_checkpoint()
        if saved is not None:
            self._result = saved
        # Find the next phase to run
        completed_phases = {
            p.phase for p in self._result.phases if p.success
        }
        for phase in PHASE_ORDER:
            if phase in completed_phases:
                continue
            self._result.current_phase = phase
            phase_result = self._execute_phase(phase)
            self._result.phases.append(phase_result)
            self._save_checkpoint()
            if not phase_result.success:
                self._result.failed_phase = phase
                self._result.current_phase = AuditPhase.FAILED
                return self._result
        self._result.current_phase = AuditPhase.COMPLETED
        self._result.completed_at = time.time()
        self._save_checkpoint()
        return self._result

    def _execute_phase(self, phase: AuditPhase) -> PhaseResult:
        """Execute one phase using its registered handler."""
        handler = self._phase_handlers.get(phase)
        if handler is None:
            return PhaseResult(
                phase=phase,
                success=False,
                error=f"No handler registered for phase {phase.value}",
            )
        start = time.time()
        try:
            result = handler()
            result.duration_ms = (time.time() - start) * 1000
            return result
        except Exception as exc:
            _logger.exception("Audit phase %s failed", phase.value)
            return PhaseResult(
                phase=phase,
                success=False,
                duration_ms=(time.time() - start) * 1000,
                error=str(exc),
            )

    def _checkpoint_path(self) -> Path | None:
        if self._checkpoint_dir is None:
            return None
        self._checkpoint_dir.mkdir(parents=True, exist_ok=True)
        return self._checkpoint_dir / f"audit_{self.audit_id}.json"

    def _save_checkpoint(self) -> None:
        path = self._checkpoint_path()
        if path is None:
            return
        try:
            path.write_text(
                json.dumps(self._result.to_dict(), indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            _logger.warning("Failed to save audit checkpoint: %s", exc)

    def _load_checkpoint(self) -> AuditResult | None:
        path = self._checkpoint_path()
        if path is None or not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            _logger.warning("Failed to load audit checkpoint: %s", exc)
            return None
        # Reconstruct result
        result = AuditResult(
            audit_id=data.get("audit_id", self.audit_id),
            config=self.config,
            current_phase=AuditPhase(data.get("current_phase", "discovery")),
            pages_crawled=data.get("pages_crawled", 0),
            health_score=data.get("health_score", 100),
            started_at=data.get("started_at", time.time()),
        )
        failed = data.get("failed_phase")
        if failed:
            result.failed_phase = AuditPhase(failed)
        for p in data.get("phases", []):
            result.phases.append(
                PhaseResult(
                    phase=AuditPhase(p["phase"]),
                    success=p["success"],
                    duration_ms=p.get("duration_ms", 0.0),
                    error=p.get("error", ""),
                )
            )
        return result

    def get_progress(self) -> dict[str, Any]:
        """Return a progress summary for status polling."""
        completed = sum(1 for p in self._result.phases if p.success)
        total = len(PHASE_ORDER)
        return {
            "audit_id": self.audit_id,
            "current_phase": self._result.current_phase.value,
            "phases_completed": completed,
            "phases_total": total,
            "progress_pct": round(completed / total * 100) if total else 0,
            "pages_crawled": self._result.pages_crawled,
            "is_completed": self._result.is_completed,
            "is_failed": self._result.is_failed,
        }
