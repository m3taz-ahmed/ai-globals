#!/usr/bin/env python3
"""Core SpecEngine: CRUD, phase gates, deltas, and manifests."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runtime.spec.analysis import AnalysisMixin
from runtime.spec.models import (
    PHASE_ORDER,
    DeltaType,
    Requirement,
    Spec,
    SpecDelta,
    SpecManifest,
    SpecPhase,
    Task,
)
from runtime.spec.scaffold import ScaffoldingMixin


class _SpecValidator:
    """Phase-gate and delta validation logic extracted from SpecEngine."""

    @staticmethod
    def phase_gate(spec: Spec) -> str | None:
        """Return a blocking reason for advancing *spec*, or None if allowed.

        WS-E W1: Tasks must be verified (not just "done") to advance.
        WS-E W2: Constitution violations block advancement from SPECIFY.
        """
        if spec.phase == SpecPhase.SPECIFY:
            if not spec.requirements:
                return "No requirements defined"
            violations = _SpecValidator.constitution_violations(spec)
            if violations:
                return f"Constitution violations: {violations[:2]}"
        if spec.phase == SpecPhase.PLAN and not spec.plan:
            return "No plan defined"
        if spec.phase == SpecPhase.TASKS and not spec.tasks:
            return "No tasks defined"
        if spec.phase == SpecPhase.IMPLEMENT:
            pending = [t.id for t in spec.tasks if t.status != "done"]
            if pending:
                return f"Tasks not done: {pending}"
            unverified = [t.id for t in spec.tasks if t.status == "done" and not t.verified]
            if unverified:
                return f"Tasks not verified: {unverified}"
        if spec.phase == SpecPhase.DONE:
            return "Already done"
        return None

    @staticmethod
    def constitution_violations(spec: Spec) -> list[str]:
        """WS-E W2: Check requirements against constitution principles.

        Returns a list of violation descriptions. A violation occurs when
        a constitution MUST principle is not reflected in any requirement.
        Uses all significant words (not just the first) for matching.
        """
        import re

        if not spec.constitution or "{{" in spec.constitution:
            return []
        violations: list[str] = []
        must_principles = re.findall(
            r"MUST\s+(.+?)(?:[.!?;:]|\n|$)", spec.constitution, re.IGNORECASE
        )
        all_req_text = " ".join(r.description.lower() for r in spec.requirements)
        _stop = {"the", "a", "an", "all", "be", "use", "include", "ensure", "provide", "support"}
        for principle in must_principles[:10]:
            words = re.findall(r"\b[a-z]{4,}\b", principle.lower())
            keywords = [w for w in words if w not in _stop]
            if not keywords:
                continue
            if not any(kw in all_req_text for kw in keywords):
                violations.append(principle.strip()[:80])
        return violations

    @staticmethod
    def validate_deltas(spec: Spec) -> list[str]:
        """WS-E W6: Validate deltas before applying.

        Checks:
        - MODIFIED/REMOVED deltas reference existing requirements
        - ADDED deltas don't duplicate existing requirement IDs
        - All deltas have non-empty descriptions (for ADDED/MODIFIED)
        """
        errors: list[str] = []
        existing_ids = {r.id for r in spec.requirements}
        for delta in spec.deltas:
            if delta.delta_type == DeltaType.ADDED:
                if delta.requirement_id in existing_ids:
                    errors.append(f"ADDED delta {delta.requirement_id} already exists")
                if not delta.description.strip():
                    errors.append(f"ADDED delta {delta.requirement_id} has empty description")
            elif delta.delta_type == DeltaType.MODIFIED:
                if delta.requirement_id not in existing_ids:
                    errors.append(f"MODIFIED delta {delta.requirement_id} not found in requirements")
                if not delta.description.strip():
                    errors.append(f"MODIFIED delta {delta.requirement_id} has empty description")
            elif delta.delta_type == DeltaType.REMOVED:
                if delta.requirement_id not in existing_ids:
                    errors.append(f"REMOVED delta {delta.requirement_id} not found in requirements")
        return errors


def _render_markdown(spec: Spec) -> str:
    """Render the spec as a Markdown artifact string."""
    requirements_state = "validated" if spec.phase.value >= SpecPhase.PLAN.value else "pending"
    lines: list[str] = [
        f"# Spec: {spec.title}",
        "",
        f"**ID:** {spec.id}  ",
        f"**Phase:** {spec.phase.value}  ",
        f"**Created:** {spec.created_at}  ",
        f"**Updated:** {spec.updated_at}",
        "",
    ]
    if spec.description:
        lines.extend(["## Description", "", spec.description, ""])
    if spec.constitution:
        lines.extend(["## Constitution", "", spec.constitution, ""])
    if spec.requirements:
        lines.extend([f"## Requirements ({requirements_state})", ""])
        for r in spec.requirements:
            lines.append(f"- [{r.priority.upper()}] **{r.id}**: {r.description}")
            if r.user_story:
                lines.append(f"  - As a user: {r.user_story}")
        lines.append("")
    if spec.plan:
        lines.extend(["## Plan", "", "```json", json.dumps(spec.plan, indent=2), "```", ""])
    if spec.tasks:
        lines.extend(["## Tasks", ""])
        checkbox_map = {"pending": "[ ]", "in_progress": "[~]", "done": "[x]", "blocked": "[!]"}
        for t in spec.tasks:
            checkbox = checkbox_map.get(t.status, "[ ]")
            deps = f" (depends: {', '.join(t.depends_on)})" if t.depends_on else ""
            est = f" ({t.estimate_hours}h)" if t.estimate_hours else ""
            lines.append(f"- {checkbox} **{t.id}**: {t.description}{deps}{est}")
        lines.append("")
    return "\n".join(lines)


class _SpecDriftHelper:
    """Drift detection and manifest tracking for SpecEngine."""

    def __init__(self, engine: SpecEngine) -> None:
        self._engine = engine

    def get_manifest(self, spec_id: str) -> SpecManifest:
        """Get the hash-tracked manifest for a spec's files."""
        manifest = SpecManifest()
        json_path = self._engine._spec_path(spec_id)
        md_path = self._engine._spec_md_path(spec_id)
        if json_path.exists():
            manifest.record_file(json_path.name, json_path.read_text(encoding="utf-8"))
        if md_path.exists():
            manifest.record_file(md_path.name, md_path.read_text(encoding="utf-8"))
        return manifest

    def is_file_modified(self, spec_id: str, file_type: str = "json") -> bool:
        """Check if a spec file was modified since last manifest recording."""
        spec = self._engine.load_spec(spec_id)
        if spec is None:
            return True
        manifest = self.get_manifest(spec_id)
        path = self._engine._spec_path(spec_id) if file_type == "json" else self._engine._spec_md_path(spec_id)
        if not path.exists():
            return True
        return manifest.is_modified(path.name, path.read_text(encoding="utf-8"))

    def detect_drift(self, spec_id: str) -> dict[str, Any]:
        """WS-E W4: Drift v2 — detect and report spec drift.

        Compares the current spec state against its manifest to identify:
        - Files modified since last manifest recording
        - Requirements added/removed since last save (via deltas)
        - Phase regressions (phase moved backwards)
        """
        spec = self._engine.load_spec(spec_id)
        if spec is None:
            return {"error": f"Spec not found: {spec_id}"}
        manifest = self.get_manifest(spec_id)
        drift_items: list[dict[str, Any]] = []
        drift_items.extend(self._check_file_drift(spec_id, manifest))
        drift_items.extend(self._check_delta_drift(spec))
        drift_items.extend(self._check_phase_regression(spec))
        return {
            "spec_id": spec_id,
            "drift_count": len(drift_items),
            "items": drift_items,
            "has_drift": len(drift_items) > 0,
        }

    def _check_file_drift(
        self, spec_id: str, manifest: SpecManifest
    ) -> list[dict[str, Any]]:
        """Check JSON and MD files for modifications since manifest recording."""
        items: list[dict[str, Any]] = []
        json_path = self._engine._spec_path(spec_id)
        if json_path.exists() and manifest.is_modified(
            json_path.name, json_path.read_text(encoding="utf-8")
        ):
            items.append({"file": json_path.name, "type": "modified", "severity": "high"})
        md_path = self._engine._spec_md_path(spec_id)
        if md_path.exists() and manifest.is_modified(
            md_path.name, md_path.read_text(encoding="utf-8")
        ):
            items.append({"file": md_path.name, "type": "modified", "severity": "medium"})
        return items

    def _check_delta_drift(self, spec: Spec) -> list[dict[str, Any]]:
        """Check for unapplied deltas indicating requirement drift."""
        if not spec.deltas:
            return []
        return [{
            "file": "deltas",
            "type": "unapplied_deltas",
            "count": len(spec.deltas),
            "severity": "high",
        }]

    def _check_phase_regression(self, spec: Spec) -> list[dict[str, Any]]:
        """Check state history for phase regressions (backward moves)."""
        items: list[dict[str, Any]] = []
        if len(spec.state_history) < 2:
            return items
        phases = [t["to"] for t in spec.state_history]
        for i in range(1, len(phases)):
            try:
                curr_idx = PHASE_ORDER.index(SpecPhase(phases[i]))
                prev_idx = PHASE_ORDER.index(SpecPhase(phases[i - 1]))
                if curr_idx < prev_idx:
                    items.append({
                        "file": "state_history",
                        "type": "phase_regression",
                        "from": phases[i - 1],
                        "to": phases[i],
                        "severity": "critical",
                    })
            except ValueError:
                continue
        return items

    def list_specs_paginated(
        self, page: int = 1, page_size: int = 20
    ) -> dict[str, Any]:
        """WS-E W5: Scale paths — paginated spec listing for large repos.

        Returns a paginated result with items, total, page, and has_more.
        """
        all_specs = self._engine.list_specs()
        total = len(all_specs)
        start = (page - 1) * page_size
        end = start + page_size
        items = all_specs[start:end]
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": end < total,
        }


class _SpecContentHelper:
    """Phase content operations (requirements, plan, tasks, verification)."""

    def __init__(self, engine: SpecEngine) -> None:
        self._e = engine

    def add_requirement(self, spec_id: str, description: str, priority: str = "must", user_story: str = "") -> Requirement:
        """Add a requirement to a spec (Specify phase)."""
        spec = self._e._require_phase(spec_id, SpecPhase.SPECIFY, "add requirements")
        req_id = f"REQ-{len(spec.requirements) + 1:03d}"
        req = Requirement(id=req_id, description=description, priority=priority, user_story=user_story)
        spec.requirements.append(req)
        self._e._save(spec)
        return req

    def set_plan(self, spec_id: str, plan: dict[str, Any]) -> None:
        """Set the technical plan (Plan phase)."""
        spec = self._e._require_phase(spec_id, SpecPhase.PLAN, "set plan")
        spec.plan = plan
        self._e._save(spec)

    def add_task(self, spec_id: str, description: str, depends_on: list[str] | None = None, estimate_hours: float = 0.0) -> Task:
        """Add a task to a spec (Tasks phase)."""
        spec = self._e._require_phase(spec_id, SpecPhase.TASKS, "add tasks")
        task_id = f"TASK-{len(spec.tasks) + 1:03d}"
        task = Task(id=task_id, description=description, depends_on=depends_on or [], estimate_hours=estimate_hours)
        spec.tasks.append(task)
        self._e._save(spec)
        return task

    def update_task_status(self, spec_id: str, task_id: str, status: str) -> bool:
        """Update a task's status (Implement phase). WS-E W1: done requires evidence."""
        spec = self._e.load_spec(spec_id)
        if spec is None:
            return False
        for task in spec.tasks:
            if task.id == task_id:
                task.status = status
                if status == "done" and task.verification_evidence:
                    task.verified = True
                elif status != "done":
                    task.verified = False
                self._e._save(spec)
                return True
        return False

    def verify_task(self, spec_id: str, task_id: str, evidence: str) -> bool:
        """WS-E W1: Provide verification evidence for a task."""
        spec = self._e.load_spec(spec_id)
        if spec is None:
            return False
        for task in spec.tasks:
            if task.id == task_id:
                task.verification_evidence = evidence
                task.verified = bool(evidence.strip())
                if task.verified and task.status != "done":
                    task.status = "done"
                self._e._save(spec)
                return True
        return False


class SpecEngine(ScaffoldingMixin, AnalysisMixin):
    """Engine for managing spec-driven development.

    Composed of:
    - :class:`~runtime.spec.scaffold.ScaffoldingMixin` — template artifacts
    - :class:`~runtime.spec.analysis.AnalysisMixin` — analyze/converge
    """

    def __init__(self, specs_dir: Path) -> None:
        self.specs_dir = specs_dir
        self.specs_dir.mkdir(parents=True, exist_ok=True)
        self._drift = _SpecDriftHelper(self)
        self._content = _SpecContentHelper(self)

    # --- Paths ---------------------------------------------------------------

    def _spec_path(self, spec_id: str) -> Path:
        """Get the file path for a spec."""
        return self.specs_dir / f"{spec_id}.json"

    def _spec_md_path(self, spec_id: str) -> Path:
        """Get the markdown artifact path for a spec."""
        return self.specs_dir / f"{spec_id}.md"

    # --- CRUD ----------------------------------------------------------------

    def init_spec(
        self, spec_id: str, title: str, description: str = "", constitution: str = ""
    ) -> Spec:
        """Initialize a new specification."""
        if self._spec_path(spec_id).exists():
            raise ValueError(f"Spec already exists: {spec_id}")
        now = datetime.now(timezone.utc).isoformat()
        spec = Spec(
            id=spec_id,
            title=title,
            description=description,
            created_at=now,
            updated_at=now,
            constitution=constitution,
        )
        self._save(spec)
        return spec

    def load_spec(self, spec_id: str) -> Spec | None:
        """Load a specification by ID."""
        path = self._spec_path(spec_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return Spec.from_dict(data)

    def _save(self, spec: Spec) -> None:
        """Save a spec to disk (JSON state + Markdown artifact)."""
        spec.updated_at = datetime.now(timezone.utc).isoformat()
        self._spec_path(spec.id).write_text(
            json.dumps(spec.to_dict(), indent=2), encoding="utf-8",
        )
        self._write_markdown(spec)

    def list_specs(self) -> list[dict[str, Any]]:
        """List all specs."""
        specs: list[dict[str, Any]] = []
        for path in self.specs_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                specs.append({
                    "id": data["id"],
                    "title": data["title"],
                    "phase": data["phase"],
                    "requirements": len(data.get("requirements", [])),
                    "tasks": len(data.get("tasks", [])),
                })
            except (json.JSONDecodeError, KeyError):
                continue
        return specs

    def delete_spec(self, spec_id: str) -> bool:
        """Delete a spec."""
        deleted = False
        json_path = self._spec_path(spec_id)
        md_path = self._spec_md_path(spec_id)
        if json_path.exists():
            json_path.unlink()
            deleted = True
        if md_path.exists():
            md_path.unlink()
        return deleted

    # --- Phase content (delegates to _SpecContentHelper) ---

    def add_requirement(self, spec_id: str, description: str, priority: str = "must", user_story: str = "") -> Requirement:
        return self._content.add_requirement(spec_id, description, priority, user_story)

    def set_plan(self, spec_id: str, plan: dict[str, Any]) -> None:
        self._content.set_plan(spec_id, plan)

    def add_task(self, spec_id: str, description: str, depends_on: list[str] | None = None, estimate_hours: float = 0.0) -> Task:
        return self._content.add_task(spec_id, description, depends_on, estimate_hours)

    def update_task_status(self, spec_id: str, task_id: str, status: str) -> bool:
        return self._content.update_task_status(spec_id, task_id, status)

    def verify_task(self, spec_id: str, task_id: str, evidence: str) -> bool:
        return self._content.verify_task(spec_id, task_id, evidence)

    # --- Phase transitions -----------------------------------------------------

    def advance(self, spec_id: str) -> Spec:
        """Advance a spec to the next phase with validation.

        WS-E W3: Records state transitions in state_history for audit trail.
        """
        spec = self.load_spec(spec_id)
        if spec is None:
            raise ValueError(f"Spec not found: {spec_id}")
        reason = _SpecValidator.phase_gate(spec)
        if reason is not None:
            if spec.phase == SpecPhase.DONE:
                raise ValueError("Spec is already done")
            if spec.phase == SpecPhase.IMPLEMENT and "not done" in reason.lower():
                raise ValueError("Cannot advance: not all tasks are done")
            if spec.phase == SpecPhase.IMPLEMENT and "not verified" in reason.lower():
                raise ValueError(f"Cannot advance: {reason}")
            raise ValueError(f"Cannot advance: {reason[0].lower()}{reason[1:]}")
        current_idx = PHASE_ORDER.index(spec.phase)
        old_phase = spec.phase
        spec.phase = PHASE_ORDER[current_idx + 1]
        spec.state_history.append({
            "from": old_phase.value,
            "to": spec.phase.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        self._save(spec)
        return spec

    def can_advance(self, spec_id: str) -> tuple[bool, str]:
        """Check if a spec can advance to the next phase."""
        spec = self.load_spec(spec_id)
        if spec is None:
            return False, "Spec not found"
        reason = _SpecValidator.phase_gate(spec)
        if reason is not None:
            return False, reason
        return True, "OK"

    def _require_phase(self, spec_id: str, phase: SpecPhase, verb: str) -> Spec:
        """Load a spec and assert it is in *phase* (for phase-scoped edits)."""
        spec = self.load_spec(spec_id)
        if spec is None:
            raise ValueError(f"Spec not found: {spec_id}")
        if spec.phase != phase:
            raise ValueError(f"Cannot {verb} in {spec.phase.value} phase")
        return spec

    # --- Deltas & manifest ------------------------------------------------------

    def add_delta(
        self,
        spec_id: str,
        requirement_id: str,
        delta_type: DeltaType,
        description: str = "",
        old_description: str = "",
        priority: str = "must",
    ) -> SpecDelta:
        """Add a delta change to a spec (ADDED/MODIFIED/REMOVED)."""
        spec = self.load_spec(spec_id)
        if spec is None:
            raise ValueError(f"Spec not found: {spec_id}")
        delta = SpecDelta(
            requirement_id=requirement_id,
            delta_type=delta_type,
            description=description,
            old_description=old_description,
            priority=priority,
        )
        spec.deltas.append(delta)
        self._save(spec)
        return delta

    def apply_deltas(self, spec_id: str) -> int:
        """Apply all deltas to the spec's requirements and clear them.

        WS-E W6: Delta hardening — validates deltas before applying.
        Returns the number of deltas applied.
        """
        spec = self.load_spec(spec_id)
        if spec is None:
            raise ValueError(f"Spec not found: {spec_id}")
        errors = _SpecValidator.validate_deltas(spec)
        if errors:
            raise ValueError(f"Delta validation failed: {'; '.join(errors)}")
        for delta in spec.deltas:
            self._apply_single_delta(spec, delta)
        applied = len(spec.deltas)
        spec.deltas.clear()
        self._save(spec)
        return applied

    def _apply_single_delta(self, spec: Spec, delta: SpecDelta) -> None:
        """Apply one delta to the spec's requirements in place."""
        if delta.delta_type == DeltaType.ADDED:
            req = Requirement(
                id=delta.requirement_id,
                description=delta.description,
                priority=delta.priority,
            )
            spec.requirements.append(req)
        elif delta.delta_type == DeltaType.MODIFIED:
            for req in spec.requirements:
                if req.id == delta.requirement_id:
                    req.description = delta.description
                    break
        elif delta.delta_type == DeltaType.REMOVED:
            spec.requirements = [
                r for r in spec.requirements if r.id != delta.requirement_id
            ]

    def get_manifest(self, spec_id: str) -> SpecManifest:
        """Get the hash-tracked manifest for a spec's files."""
        return self._drift.get_manifest(spec_id)

    def is_file_modified(self, spec_id: str, file_type: str = "json") -> bool:
        """Check if a spec file was modified since last manifest recording."""
        return self._drift.is_file_modified(spec_id, file_type)

    def detect_drift(self, spec_id: str) -> dict[str, Any]:
        """WS-E W4: Drift v2 — detect and report spec drift."""
        return self._drift.detect_drift(spec_id)

    def list_specs_paginated(
        self, page: int = 1, page_size: int = 20
    ) -> dict[str, Any]:
        """WS-E W5: Scale paths — paginated spec listing for large repos."""
        return self._drift.list_specs_paginated(page, page_size)

    def _write_markdown(self, spec: Spec) -> None:
        """Write the spec as a Markdown artifact."""
        self._spec_md_path(spec.id).write_text(
            _render_markdown(spec), encoding="utf-8"
        )
