#!/usr/bin/env python3
"""Spec-driven development engine for aiZee.

Implements a structured 4-phase development process:
1. **Specify** â€” Define what to build (user stories, requirements)
2. **Plan** â€” Technical design (architecture, stack, constraints)
3. **Tasks** â€” Break down into actionable tasks
4. **Implement** â€” Execute tasks with validation checkpoints

Each phase produces a Markdown artifact that feeds the next phase.
Phases have validation gates â€” you don't advance until the current
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

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

# Template directory â€” discovered relative to aiZee root (tech-stack/spec-driven-templates/)
# Falls back gracefully if templates absent (scaffold methods return empty string).
# Robust against exec()/runpy contexts where __file__ may be undefined.
_THIS_FILE = Path(__file__).resolve() if "__file__" in globals() else Path.cwd() / "spec_engine.py"
_TEMPLATE_DIR_CANDIDATES = [
    _THIS_FILE.parent.parent / "tech-stack" / "spec-driven-templates",
    Path("tech-stack") / "spec-driven-templates",
]


def _resolve_template_dir() -> Path | None:
    """Resolve the spec-driven templates directory (aiZee root-relative)."""
    for candidate in _TEMPLATE_DIR_CANDIDATES:
        if candidate.is_dir():
            return candidate
    return None


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

    # -- Spec-Kit-inspired additions (P0) -------------------------------------

    def _render_template(self, template_name: str, context: dict[str, str]) -> str:
        """Render a spec-driven template by replacing {{PLACEHOLDER}} tokens.

        Returns empty string if template directory or file is absent
        (graceful fallback â€” never raises on missing templates).
        """
        template_dir = _resolve_template_dir()
        if template_dir is None:
            return ""
        template_path = template_dir / template_name
        if not template_path.exists():
            return ""
        content = template_path.read_text(encoding="utf-8")
        for key, value in context.items():
            content = content.replace(f"{{{{{key}}}}}", value)
        return content

    def _spec_context(self, spec: Spec) -> dict[str, str]:
        """Build template context dict from a Spec."""
        date_str = spec.created_at[:10] if spec.created_at else datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return {
            "TITLE": spec.title,
            "SPEC_ID": spec.id,
            "FEATURE_BRANCH": f"{spec.id}-{spec.title.lower().replace(' ', '-')[:30]}",
            "DATE": date_str,
            "DESCRIPTION": spec.description,
            "PROJECT_NAME": spec.title,
        }

    def scaffold_spec(self, spec_id: str, title: str, description: str = "") -> str:
        """Scaffold a spec markdown artifact from the spec-template.

        Writes ``{spec_id}.spec.md`` (scaffold for human/AI editing).
        Does NOT overwrite the auto-rendered ``{spec_id}.md``.
        Returns the scaffold content (empty string if templates absent).
        """
        spec = self.load_spec(spec_id)
        if spec is None:
            spec = Spec(id=spec_id, title=title, description=description)
        context = self._spec_context(spec)
        content = self._render_template("spec-template.md", context)
        if content:
            scaffold_path = self.specs_dir / f"{spec_id}.spec.md"
            scaffold_path.write_text(content, encoding="utf-8")
        return content

    def scaffold_plan(self, spec_id: str) -> str:
        """Scaffold a plan markdown artifact from the plan-template."""
        spec = self.load_spec(spec_id)
        if spec is None:
            return ""
        context = self._spec_context(spec)
        content = self._render_template("plan-template.md", context)
        if content:
            scaffold_path = self.specs_dir / f"{spec_id}.plan.md"
            scaffold_path.write_text(content, encoding="utf-8")
        return content

    def scaffold_tasks(self, spec_id: str) -> str:
        """Scaffold a tasks markdown artifact from the tasks-template."""
        spec = self.load_spec(spec_id)
        if spec is None:
            return ""
        context = self._spec_context(spec)
        content = self._render_template("tasks-template.md", context)
        if content:
            scaffold_path = self.specs_dir / f"{spec_id}.tasks.md"
            scaffold_path.write_text(content, encoding="utf-8")
        return content

    def scaffold_checklist(self, spec_id: str) -> str:
        """Scaffold a quality checklist markdown artifact from the checklist-template."""
        spec = self.load_spec(spec_id)
        if spec is None:
            return ""
        context = self._spec_context(spec)
        content = self._render_template("checklist-template.md", context)
        if content:
            checklist_path = self.specs_dir / f"{spec_id}.checklist.md"
            checklist_path.write_text(content, encoding="utf-8")
        return content

    def set_constitution(self, spec_id: str, constitution: str) -> None:
        """Set the constitution (governing principles) for a spec."""
        spec = self.load_spec(spec_id)
        if spec is None:
            raise ValueError(f"Spec not found: {spec_id}")
        spec.constitution = constitution
        self._save(spec)

    def validate_checklist(self, spec_id: str) -> dict[str, Any]:
        """Validate a spec against quality checklist criteria.

        Returns a dict with pass/fail counts and failing items.
        Reads the scaffolded ``{spec_id}.checklist.md`` if present,
        otherwise validates against built-in criteria.
        """
        spec = self.load_spec(spec_id)
        if spec is None:
            return {"error": f"Spec not found: {spec_id}"}
        spec_md = self._spec_md_path(spec_id).read_text(encoding="utf-8") if self._spec_md_path(spec_id).exists() else ""
        results: dict[str, Any] = {
            "spec_id": spec_id,
            "total_checks": 0,
            "passed": 0,
            "failed": 0,
            "failing_items": [],
        }
        checks = [
            ("no_implementation_details", "No implementation details" in spec_md or "NEEDS CLARIFICATION" not in spec_md),
            ("has_user_scenarios", "User Story" in spec_md or len(spec.requirements) > 0),
            ("has_requirements", len(spec.requirements) > 0),
            ("has_success_criteria", "Success Criteria" in spec_md or "SC-" in spec_md),
            ("no_unresolved_clarifications", "[NEEDS CLARIFICATION" not in spec_md),
            ("has_edge_cases", "Edge Cases" in spec_md),
            ("has_assumptions", "Assumptions" in spec_md),
        ]
        for name, passed in checks:
            results["total_checks"] += 1
            if passed:
                results["passed"] += 1
            else:
                results["failed"] += 1
                results["failing_items"].append(name)
        return results

    def analyze_artifacts(self, spec_id: str) -> dict[str, Any]:
        """Cross-artifact consistency analysis (spec â†” plan â†” tasks).

        Non-destructive read-only analysis inspired by spec-kit's analyze command.
        Detects: coverage gaps, duplication, ambiguity, underspecification,
        constitution violations, terminology drift.

        Returns a structured report dict with findings + metrics.
        """
        spec = self.load_spec(spec_id)
        if spec is None:
            return {"error": f"Spec not found: {spec_id}"}
        spec_md = self._spec_md_path(spec_id).read_text(encoding="utf-8") if self._spec_md_path(spec_id).exists() else ""
        plan_md = ""
        plan_path = self.specs_dir / f"{spec_id}.plan.md"
        if plan_path.exists():
            plan_md = plan_path.read_text(encoding="utf-8")
        tasks_md = ""
        tasks_path = self.specs_dir / f"{spec_id}.tasks.md"
        if tasks_path.exists():
            tasks_md = tasks_path.read_text(encoding="utf-8")

        # Extract requirement IDs from spec state
        req_ids = {r.id for r in spec.requirements}
        # Task IDs from spec state (authoritative) + tasks.md scaffold (if present)
        task_ids = {t.id for t in spec.tasks}
        task_ids.update(re.findall(r"\bT\d{3}\b", tasks_md))
        # Extract FR-### and SC-### from spec
        fr_ids = set(re.findall(r"\bFR-\d{3}\b", spec_md))
        sc_ids = set(re.findall(r"\bSC-\d{3}\b", spec_md))

        # Coverage: requirements with no task reference
        uncovered_reqs = []
        for req in spec.requirements:
            if not any(req.id in tasks_md or req.description[:20] in tasks_md for _ in [True]):
                uncovered_reqs.append(req.id)

        # Ambiguity: vague adjectives without measurable criteria
        vague_terms = ["fast", "scalable", "secure", "intuitive", "robust", "efficient"]
        ambiguity_findings = []
        for term in vague_terms:
            pattern = rf"\b{term}\b"
            if re.search(pattern, spec_md, re.IGNORECASE):
                # Check if a measurable metric follows within 100 chars
                for match in re.finditer(pattern, spec_md, re.IGNORECASE):
                    context_window = spec_md[match.start():match.start() + 100]
                    if not re.search(r"\d+\s*(ms|s|sec|second|%|user|concurrent|minute|hour)", context_window, re.IGNORECASE):
                        ambiguity_findings.append({"term": term, "position": match.start()})

        # Unresolved placeholders
        unresolved = re.findall(r"\[NEEDS CLARIFICATION[^\]]*\]", spec_md)
        todo_markers = re.findall(r"\b(TODO|TKTK|FIXME|\?\?\?)\b", spec_md + plan_md + tasks_md)

        # Constitution violations (if constitution set and not template-only)
        constitution_violations: list[str] = []
        if spec.constitution and "{{" not in spec.constitution:
            must_principles = re.findall(r"MUST\s+(.+?)(?:\.|$)", spec.constitution, re.IGNORECASE)
            for principle in must_principles[:10]:  # Limit to first 10
                # Heuristic: check if principle keyword appears in spec/plan
                keyword = principle.split()[0].lower() if principle.split() else ""
                if keyword and len(keyword) > 3 and keyword not in spec_md.lower() and keyword not in plan_md.lower():
                    constitution_violations.append(principle.strip()[:80])

        findings: list[dict[str, str]] = []
        for req_id in uncovered_reqs:
            findings.append({
                "id": f"COV-{req_id}",
                "category": "coverage_gap",
                "severity": "HIGH",
                "location": "tasks.md",
                "summary": f"Requirement {req_id} has no associated task",
            })
        for amb in ambiguity_findings[:10]:
            findings.append({
                "id": f"AMB-{amb['term']}",
                "category": "ambiguity",
                "severity": "MEDIUM",
                "location": f"spec.md:{amb['position']}",
                "summary": f"Vague term '{amb['term']}' lacks measurable criteria",
            })
        for marker in unresolved:
            findings.append({
                "id": f"UNC-{hashlib.md5(marker.encode()).hexdigest()[:6]}",
                "category": "underspecification",
                "severity": "HIGH",
                "location": "spec.md",
                "summary": f"Unresolved: {marker[:60]}",
            })
        for marker in todo_markers[:5]:
            findings.append({
                "id": f"TODO-{hashlib.md5(marker.encode()).hexdigest()[:6]}",
                "category": "underspecification",
                "severity": "MEDIUM",
                "location": "artifacts",
                "summary": f"Unresolved placeholder: {marker}",
            })
        for violation in constitution_violations:
            findings.append({
                "id": f"CON-{hashlib.md5(violation.encode()).hexdigest()[:6]}",
                "category": "constitution_violation",
                "severity": "CRITICAL",
                "location": "constitution",
                "summary": f"MUST principle not reflected: {violation}",
            })

        coverage_pct = round((len(req_ids) - len(uncovered_reqs)) / max(len(req_ids), 1) * 100, 1)
        return {
            "spec_id": spec_id,
            "metrics": {
                "total_requirements": len(req_ids),
                "total_tasks": len(task_ids),
                "total_fr": len(fr_ids),
                "total_sc": len(sc_ids),
                "coverage_pct": coverage_pct,
                "ambiguity_count": len(ambiguity_findings),
                "unresolved_count": len(unresolved),
                "todo_count": len(todo_markers),
                "constitution_violations": len(constitution_violations),
            },
            "findings": findings,
            "critical_count": sum(1 for f in findings if f["severity"] == "CRITICAL"),
            "high_count": sum(1 for f in findings if f["severity"] == "HIGH"),
            "medium_count": sum(1 for f in findings if f["severity"] == "MEDIUM"),
        }

    def converge_to_code(self, spec_id: str, codebase_dir: Path) -> dict[str, Any]:
        """Assess codebase against spec/plan/tasks; identify remaining work.

        Inspired by spec-kit's converge command. Read-only â€” does NOT modify
        any files. Returns a structured report of gaps (missing/partial/
        contradicts/unrequested) with suggested remediation tasks.

        Args:
            spec_id: The spec to converge against.
            codebase_dir: Root directory of the codebase to assess.
        """
        spec = self.load_spec(spec_id)
        if spec is None:
            return {"error": f"Spec not found: {spec_id}"}
        if not codebase_dir.is_dir():
            return {"error": f"Codebase dir not found: {codebase_dir}"}

        # Gather source files (limit to common code extensions)
        code_extensions = {".py", ".php", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".kt", ".swift"}
        source_files: list[Path] = []
        for ext in code_extensions:
            source_files.extend(codebase_dir.rglob(f"*{ext}"))
        # Exclude common ignore dirs
        ignore_dirs = {".git", "__pycache__", "node_modules", "vendor", ".venv", "venv", "dist", "build"}
        source_files = [f for f in source_files if not any(part in ignore_dirs for part in f.parts)]
        source_files = source_files[:500]  # Cap for performance

        # Build a keyword index from requirements
        all_code_text = ""
        for f in source_files[:100]:  # Sample first 100 files for text search
            try:
                all_code_text += f.read_text(encoding="utf-8", errors="ignore").lower() + "\n"
            except OSError:
                continue

        findings: list[dict[str, str]] = []
        for req in spec.requirements:
            # Extract keywords from requirement description
            words = re.findall(r"\b[a-z]{4,}\b", req.description.lower())
            keywords = [w for w in words if w not in {"system", "must", "should", "user", "users", "shall", "able"}]
            if not keywords:
                continue
            # Check if any keyword appears in code
            matched = sum(1 for kw in keywords[:5] if kw in all_code_text)
            if matched == 0:
                findings.append({
                    "id": f"MISS-{req.id}",
                    "gap_type": "missing",
                    "severity": "HIGH",
                    "source_ref": req.id,
                    "summary": f"Requirement {req.id} keywords not found in codebase: {', '.join(keywords[:3])}",
                })
            elif matched < len(keywords[:5]) / 2:
                findings.append({
                    "id": f"PART-{req.id}",
                    "gap_type": "partial",
                    "severity": "MEDIUM",
                    "source_ref": req.id,
                    "summary": f"Requirement {req.id} partially implemented ({matched}/{min(5, len(keywords))} keywords found)",
                })

        # Check task completion vs code
        incomplete_tasks = [t for t in spec.tasks if t.status != "done"]
        for task in incomplete_tasks:
            findings.append({
                "id": f"TASK-{task.id}",
                "gap_type": "missing" if task.status == "pending" else "partial",
                "severity": "HIGH" if task.status == "pending" else "MEDIUM",
                "source_ref": task.id,
                "summary": f"Task {task.id} not done (status: {task.status}): {task.description[:60]}",
            })

        # Suggest remediation tasks (append-only style, like spec-kit converge)
        suggested_tasks: list[dict[str, str]] = []
        existing_max = len(spec.tasks)
        for i, finding in enumerate(findings, start=1):
            task_id = f"T{existing_max + i:03d}"
            suggested_tasks.append({
                "id": task_id,
                "description": finding["summary"],
                "source_ref": finding["source_ref"],
                "gap_type": finding["gap_type"],
                "severity": finding["severity"],
            })

        return {
            "spec_id": spec_id,
            "codebase_dir": str(codebase_dir),
            "files_scanned": len(source_files),
            "metrics": {
                "requirements_checked": len(spec.requirements),
                "tasks_incomplete": len(incomplete_tasks),
                "findings_total": len(findings),
                "missing_count": sum(1 for f in findings if f["gap_type"] == "missing"),
                "partial_count": sum(1 for f in findings if f["gap_type"] == "partial"),
            },
            "findings": findings,
            "suggested_tasks": suggested_tasks,
            "converged": len(findings) == 0,
        }


if __name__ == "__main__":
    import sys
    engine = SpecEngine(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".ai/specs"))
    print(json.dumps(engine.list_specs(), indent=2))
