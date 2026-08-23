#!/usr/bin/env python3
"""Data models for spec-driven development (phases, specs, deltas, manifests)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SpecPhase(str, Enum):
    """Spec-driven development phases."""

    SPECIFY = "specify"
    PLAN = "plan"
    TASKS = "tasks"
    IMPLEMENT = "implement"
    DONE = "done"


PHASE_ORDER = [SpecPhase.SPECIFY, SpecPhase.PLAN, SpecPhase.TASKS, SpecPhase.IMPLEMENT, SpecPhase.DONE]


class DeltaType(str, Enum):
    """Delta spec change types (from OpenSpec)."""

    ADDED = "added"
    MODIFIED = "modified"
    REMOVED = "removed"


@dataclass
class SpecDelta:
    """A delta change to a spec (ADDED/MODIFIED/REMOVED).

    Inspired by OpenSpec's delta-based spec management. Deltas merge
    cleanly into main specs during archive, enabling parallel feature
    development without conflicts.
    """

    requirement_id: str
    delta_type: DeltaType
    description: str = ""
    old_description: str = ""  # For MODIFIED deltas
    priority: str = "must"


@dataclass
class SpecManifest:
    """Hash-tracked file manifest for safe spec file management (from spec-kit).

    Tracks SHA-256 hashes of generated spec files to detect manual edits
    and prevent accidental overwriting of user modifications.
    """

    files: dict[str, str] = field(default_factory=dict)  # rel_path -> sha256

    def record_file(self, rel_path: str, content: str) -> None:
        """Record a file's hash."""
        self.files[rel_path] = hashlib.sha256(content.encode("utf-8")).hexdigest()

    def is_modified(self, rel_path: str, current_content: str) -> bool:
        """Check if a file was modified since recording."""
        if rel_path not in self.files:
            return True  # New file
        current_hash = hashlib.sha256(current_content.encode("utf-8")).hexdigest()
        return current_hash != self.files[rel_path]

    def to_dict(self) -> dict[str, Any]:
        return {"files": dict(self.files)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SpecManifest:
        return cls(files=dict(data.get("files", {})))


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
    deltas: list[SpecDelta] = field(default_factory=list)  # Delta-based changes

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
            "deltas": [
                {"requirement_id": d.requirement_id, "delta_type": d.delta_type.value,
                 "description": d.description, "old_description": d.old_description,
                 "priority": d.priority}
                for d in self.deltas
            ],
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
            deltas=[
                SpecDelta(
                    requirement_id=d["requirement_id"],
                    delta_type=DeltaType(d.get("delta_type", "added")),
                    description=d.get("description", ""),
                    old_description=d.get("old_description", ""),
                    priority=d.get("priority", "must"),
                )
                for d in data.get("deltas", [])
            ],
        )
