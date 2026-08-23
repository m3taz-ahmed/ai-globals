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


class SpecEngine(ScaffoldingMixin, AnalysisMixin):
    """Engine for managing spec-driven development.

    Composed of:
    - :class:`~runtime.spec.scaffold.ScaffoldingMixin` — template artifacts
    - :class:`~runtime.spec.analysis.AnalysisMixin` — analyze/converge
    """

    def __init__(self, specs_dir: Path) -> None:
        self.specs_dir = specs_dir
        self.specs_dir.mkdir(parents=True, exist_ok=True)

    # --- Paths ---------------------------------------------------------------

    def _spec_path(self, spec_id: str) -> Path:
        """Get the file path for a spec."""
        return self.specs_dir / f"{spec_id}.json"

    def _spec_md_path(self, spec_id: str) -> Path:
        """Get the markdown artifact path for a spec."""
        return self.specs_dir / f"{spec_id}.md"

    # --- CRUD ----------------------------------------------------------------

    def init_spec(self, spec_id: str, title: str, description: str = "") -> Spec:
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

    # --- Phase content -------------------------------------------------------

    def add_requirement(self, spec_id: str, description: str, priority: str = "must", user_story: str = "") -> Requirement:
        """Add a requirement to a spec (Specify phase)."""
        spec = self._require_phase(spec_id, SpecPhase.SPECIFY, "add requirements")
        req_id = f"REQ-{len(spec.requirements) + 1:03d}"
        req = Requirement(id=req_id, description=description, priority=priority, user_story=user_story)
        spec.requirements.append(req)
        self._save(spec)
        return req

    def set_plan(self, spec_id: str, plan: dict[str, Any]) -> None:
        """Set the technical plan (Plan phase)."""
        spec = self._require_phase(spec_id, SpecPhase.PLAN, "set plan")
        spec.plan = plan
        self._save(spec)

    def add_task(
        self,
        spec_id: str,
        description: str,
        depends_on: list[str] | None = None,
        estimate_hours: float = 0.0,
    ) -> Task:
        """Add a task to a spec (Tasks phase)."""
        spec = self._require_phase(spec_id, SpecPhase.TASKS, "add tasks")
        task_id = f"TASK-{len(spec.tasks) + 1:03d}"
        task = Task(
            id=task_id,
            description=description,
            depends_on=depends_on or [],
            estimate_hours=estimate_hours,
        )
        spec.tasks.append(task)
        self._save(spec)
        return task

    def update_task_status(self, spec_id: str, task_id: str, status: str) -> bool:
        """Update a task's status (Implement phase)."""
        spec = self.load_spec(spec_id)
        if spec is None:
            return False
        for task in spec.tasks:
            if task.id == task_id:
                task.status = status
                self._save(spec)
                return True
        return False

    # --- Phase transitions -----------------------------------------------------

    @staticmethod
    def _phase_gate(spec: Spec) -> str | None:
        """Return a blocking reason for advancing *spec*, or None if allowed."""
        if spec.phase == SpecPhase.SPECIFY and not spec.requirements:
            return "No requirements defined"
        if spec.phase == SpecPhase.PLAN and not spec.plan:
            return "No plan defined"
        if spec.phase == SpecPhase.TASKS and not spec.tasks:
            return "No tasks defined"
        if spec.phase == SpecPhase.IMPLEMENT:
            pending = [t.id for t in spec.tasks if t.status != "done"]
            if pending:
                return f"Tasks not done: {pending}"
        if spec.phase == SpecPhase.DONE:
            return "Already done"
        return None

    def advance(self, spec_id: str) -> Spec:
        """Advance a spec to the next phase with validation."""
        spec = self.load_spec(spec_id)
        if spec is None:
            raise ValueError(f"Spec not found: {spec_id}")
        reason = self._phase_gate(spec)
        if reason is not None:
            # Legacy-compatible error messages.
            if spec.phase == SpecPhase.IMPLEMENT:
                raise ValueError("Cannot advance: not all tasks are done")
            if spec.phase == SpecPhase.DONE:
                raise ValueError("Spec is already done")
            raise ValueError(f"Cannot advance: {reason[0].lower()}{reason[1:]}")
        current_idx = PHASE_ORDER.index(spec.phase)
        spec.phase = PHASE_ORDER[current_idx + 1]
        self._save(spec)
        return spec

    def can_advance(self, spec_id: str) -> tuple[bool, str]:
        """Check if a spec can advance to the next phase."""
        spec = self.load_spec(spec_id)
        if spec is None:
            return False, "Spec not found"
        reason = self._phase_gate(spec)
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

        Returns the number of deltas applied.
        """
        spec = self.load_spec(spec_id)
        if spec is None:
            raise ValueError(f"Spec not found: {spec_id}")
        applied = 0
        for delta in spec.deltas:
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
            applied += 1
        spec.deltas.clear()
        self._save(spec)
        return applied

    def get_manifest(self, spec_id: str) -> SpecManifest:
        """Get the hash-tracked manifest for a spec's files."""
        manifest = SpecManifest()
        json_path = self._spec_path(spec_id)
        md_path = self._spec_md_path(spec_id)
        if json_path.exists():
            manifest.record_file(json_path.name, json_path.read_text(encoding="utf-8"))
        if md_path.exists():
            manifest.record_file(md_path.name, md_path.read_text(encoding="utf-8"))
        return manifest

    def is_file_modified(self, spec_id: str, file_type: str = "json") -> bool:
        """Check if a spec file was modified since last manifest recording."""
        spec = self.load_spec(spec_id)
        if spec is None:
            return True
        manifest = self.get_manifest(spec_id)
        path = self._spec_path(spec_id) if file_type == "json" else self._spec_md_path(spec_id)
        if not path.exists():
            return True
        return manifest.is_modified(path.name, path.read_text(encoding="utf-8"))

    # --- Markdown rendering ------------------------------------------------------

    def _write_markdown(self, spec: Spec) -> None:
        """Write the spec as a Markdown artifact."""
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
        self._spec_md_path(spec.id).write_text("\n".join(lines), encoding="utf-8")
