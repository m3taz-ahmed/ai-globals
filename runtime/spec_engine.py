#!/usr/bin/env python3
"""Spec-driven development engine for AI Global OS.

Implements a structured 4-phase development process:
1. **Specify** — Define what to build (user stories, requirements)
2. **Plan** — Technical design (architecture, stack, constraints)
3. **Tasks** — Break down into actionable tasks
4. **Implement** — Execute tasks with validation checkpoints

Each phase produces a Markdown artifact that feeds the next phase.
Phases have validation gates — you don't advance until the current
phase passes its checks.

Usage::

    from runtime.spec_engine import SpecEngine
    engine = SpecEngine(Path(".ai/specs"))
    engine.init_spec("user-auth", "User authentication feature")
    engine.add_requirement("user-auth", "Users can log in with email")
    engine.advance("user-auth")  # Specify -> Plan
    engine.set_plan("user-auth", {"stack": "FastAPI", "db": "PostgreSQL"})
    engine.advance("user-auth")  # Plan -> Tasks
    engine.add_task("user-auth", "Create User model")
    engine.advance("user-auth")  # Tasks -> Implement
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class SpecPhase(str, Enum):
    """Spec-driven development phases."""

    SPECIFY = "specify"
    PLAN = "plan"
    TASKS = "tasks"
    IMPLEMENT = "implement"
    DONE = "done"


PHASE_ORDER = [SpecPhase.SPECIFY, SpecPhase.PLAN, SpecPhase.TASKS, SpecPhase.IMPLEMENT, SpecPhase.DONE]


@dataclass
class Requirement:
    """A single requirement in the Specify phase."""

    id: str
    description: str
    priority: str = "must"  # must, should, could, won't
    user_story: str = ""


@dataclass
class Task:
    """A single task in the Tasks phase."""

    id: str
    description: str
    status: str = "pending"  # pending, in_progress, done, blocked
    depends_on: list[str] = field(default_factory=list)
    estimate_hours: float = 0.0


@dataclass
class Spec:
    """A complete specification with all phases."""

    id: str
    title: str
    description: str = ""
    phase: SpecPhase = SpecPhase.SPECIFY
    requirements: list[Requirement] = field(default_factory=list)
    plan: dict[str, Any] = field(default_factory=dict)
    tasks: list[Task] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    constitution: str = ""  # Project governing principles

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "phase": self.phase.value,
            "requirements": [
                {"id": r.id, "description": r.description, "priority": r.priority, "user_story": r.user_story}
                for r in self.requirements
            ],
            "plan": self.plan,
            "tasks": [
                {"id": t.id, "description": t.description, "status": t.status,
                 "depends_on": t.depends_on, "estimate_hours": t.estimate_hours}
                for t in self.tasks
            ],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "constitution": self.constitution,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Spec:
        return cls(
            id=data["id"],
            title=data["title"],
            description=data.get("description", ""),
            phase=SpecPhase(data.get("phase", "specify")),
            requirements=[
                Requirement(
                    id=r["id"], description=r["description"],
                    priority=r.get("priority", "must"), user_story=r.get("user_story", ""),
                )
                for r in data.get("requirements", [])
            ],
            plan=data.get("plan", {}),
            tasks=[
                Task(
                    id=t["id"], description=t["description"], status=t.get("status", "pending"),
                    depends_on=t.get("depends_on", []), estimate_hours=t.get("estimate_hours", 0.0),
                )
                for t in data.get("tasks", [])
            ],
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            constitution=data.get("constitution", ""),
        )


class SpecEngine:
    """Engine for managing spec-driven development."""

    def __init__(self, specs_dir: Path) -> None:
        self.specs_dir = specs_dir
        self.specs_dir.mkdir(parents=True, exist_ok=True)

    def _spec_path(self, spec_id: str) -> Path:
        """Get the file path for a spec."""
        return self.specs_dir / f"{spec_id}.json"

    def _spec_md_path(self, spec_id: str) -> Path:
        """Get the markdown artifact path for a spec."""
        return self.specs_dir / f"{spec_id}.md"

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
        self._write_markdown(spec)
        return spec

    def load_spec(self, spec_id: str) -> Spec | None:
        """Load a specification by ID."""
        path = self._spec_path(spec_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return Spec.from_dict(data)

    def _save(self, spec: Spec) -> None:
        """Save a spec to disk."""
        spec.updated_at = datetime.now(timezone.utc).isoformat()
        self._spec_path(spec.id).write_text(
            json.dumps(spec.to_dict(), indent=2), encoding="utf-8",
        )
        self._write_markdown(spec)

    def _write_markdown(self, spec: Spec) -> None:
        """Write the spec as a Markdown artifact."""
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
            lines.extend([f"## Requirements ({(spec.phase.value >= SpecPhase.PLAN.value and 'validated') or 'pending'})", ""])
            for r in spec.requirements:
                lines.append(f"- [{r.priority.upper()}] **{r.id}**: {r.description}")
                if r.user_story:
                    lines.append(f"  - As a user: {r.user_story}")
            lines.append("")
        if spec.plan:
            lines.extend(["## Plan", "", "```json", json.dumps(spec.plan, indent=2), "```", ""])
        if spec.tasks:
            lines.extend(["## Tasks", ""])
            for t in spec.tasks:
                checkbox = {"pending": "[ ]", "in_progress": "[~]", "done": "[x]", "blocked": "[!]"}.get(t.status, "[ ]")
                deps = f" (depends: {', '.join(t.depends_on)})" if t.depends_on else ""
                est = f" ({t.estimate_hours}h)" if t.estimate_hours else ""
                lines.append(f"- {checkbox} **{t.id}**: {t.description}{deps}{est}")
            lines.append("")
        self._spec_md_path(spec.id).write_text("\n".join(lines), encoding="utf-8")

    def add_requirement(self, spec_id: str, description: str, priority: str = "must", user_story: str = "") -> Requirement:
        """Add a requirement to a spec (Specify phase)."""
        spec = self.load_spec(spec_id)
        if spec is None:
            raise ValueError(f"Spec not found: {spec_id}")
        if spec.phase != SpecPhase.SPECIFY:
            raise ValueError(f"Cannot add requirements in {spec.phase.value} phase")
        req_id = f"REQ-{len(spec.requirements) + 1:03d}"
        req = Requirement(id=req_id, description=description, priority=priority, user_story=user_story)
        spec.requirements.append(req)
        self._save(spec)
        return req

    def set_plan(self, spec_id: str, plan: dict[str, Any]) -> None:
        """Set the technical plan (Plan phase)."""
        spec = self.load_spec(spec_id)
        if spec is None:
            raise ValueError(f"Spec not found: {spec_id}")
        if spec.phase != SpecPhase.PLAN:
            raise ValueError(f"Cannot set plan in {spec.phase.value} phase")
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
        spec = self.load_spec(spec_id)
        if spec is None:
            raise ValueError(f"Spec not found: {spec_id}")
        if spec.phase != SpecPhase.TASKS:
            raise ValueError(f"Cannot add tasks in {spec.phase.value} phase")
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

    def advance(self, spec_id: str) -> Spec:
        """Advance a spec to the next phase with validation."""
        spec = self.load_spec(spec_id)
        if spec is None:
            raise ValueError(f"Spec not found: {spec_id}")
        # Validation gates
        if spec.phase == SpecPhase.SPECIFY:
            if not spec.requirements:
                raise ValueError("Cannot advance: no requirements defined")
        elif spec.phase == SpecPhase.PLAN:
            if not spec.plan:
                raise ValueError("Cannot advance: no plan defined")
        elif spec.phase == SpecPhase.TASKS:
            if not spec.tasks:
                raise ValueError("Cannot advance: no tasks defined")
        elif spec.phase == SpecPhase.IMPLEMENT:
            if not all(t.status == "done" for t in spec.tasks):
                raise ValueError("Cannot advance: not all tasks are done")
        elif spec.phase == SpecPhase.DONE:
            raise ValueError("Spec is already done")
        # Advance
        current_idx = PHASE_ORDER.index(spec.phase)
        spec.phase = PHASE_ORDER[current_idx + 1]
        self._save(spec)
        return spec

    def can_advance(self, spec_id: str) -> tuple[bool, str]:
        """Check if a spec can advance to the next phase."""
        spec = self.load_spec(spec_id)
        if spec is None:
            return False, "Spec not found"
        if spec.phase == SpecPhase.SPECIFY:
            if not spec.requirements:
                return False, "No requirements defined"
        elif spec.phase == SpecPhase.PLAN:
            if not spec.plan:
                return False, "No plan defined"
        elif spec.phase == SpecPhase.TASKS:
            if not spec.tasks:
                return False, "No tasks defined"
        elif spec.phase == SpecPhase.IMPLEMENT:
            if not all(t.status == "done" for t in spec.tasks):
                pending = [t.id for t in spec.tasks if t.status != "done"]
                return False, f"Tasks not done: {pending}"
        elif spec.phase == SpecPhase.DONE:
            return False, "Already done"
        return True, "OK"

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


if __name__ == "__main__":
    import sys
    engine = SpecEngine(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".ai/specs"))
    print(json.dumps(engine.list_specs(), indent=2))
