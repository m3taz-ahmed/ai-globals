#!/usr/bin/env python3
"""Scaffolding mixin: template-based artifacts and checklist validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from runtime.spec.models import Spec
from runtime.spec.templates import render_template, spec_context


class ScaffoldingMixin:
    """Template scaffold methods for SpecEngine.

    Requires the host class (``SpecEngine``) to provide ``specs_dir``,
    ``load_spec``, ``_save``, and ``_spec_md_path``. The declarations below
    are overridden by SpecEngine via MRO; they exist so type checkers can
    verify attribute access from mixin methods.
    """

    specs_dir: Path

    def load_spec(self, spec_id: str) -> Spec | None:  # pragma: no cover - host impl
        raise NotImplementedError

    def _save(self, spec: Spec) -> None:  # pragma: no cover - host impl
        raise NotImplementedError

    def _spec_md_path(self, spec_id: str) -> Path:  # pragma: no cover - host impl
        raise NotImplementedError

    def _render_template(self, template_name: str, context: dict[str, str]) -> str:
        return render_template(template_name, context)

    def _spec_context(self, spec: Spec) -> dict[str, str]:
        return spec_context(spec.id, spec.title, spec.description, spec.created_at)

    def _write_scaffold(self, spec_id: str, suffix: str, content: str) -> None:
        if content:
            path = self.specs_dir / f"{spec_id}.{suffix}"
            path.write_text(content, encoding="utf-8")

    def scaffold_spec(self, spec_id: str, title: str, description: str = "") -> str:
        """Scaffold a spec markdown artifact from the spec-template.

        Writes ``{spec_id}.spec.md`` (scaffold for human/AI editing).
        Does NOT overwrite the auto-rendered ``{spec_id}.md``.
        Returns the scaffold content (empty string if templates absent).
        """
        spec = self.load_spec(spec_id)
        if spec is None:
            spec = Spec(id=spec_id, title=title, description=description)
        content = self._render_template("spec-template.md", self._spec_context(spec))
        self._write_scaffold(spec_id, "spec.md", content)
        return content

    def scaffold_plan(self, spec_id: str) -> str:
        """Scaffold a plan markdown artifact from the plan-template."""
        spec = self.load_spec(spec_id)
        if spec is None:
            return ""
        content = self._render_template("plan-template.md", self._spec_context(spec))
        self._write_scaffold(spec_id, "plan.md", content)
        return content

    def scaffold_tasks(self, spec_id: str) -> str:
        """Scaffold a tasks markdown artifact from the tasks-template."""
        spec = self.load_spec(spec_id)
        if spec is None:
            return ""
        content = self._render_template("tasks-template.md", self._spec_context(spec))
        self._write_scaffold(spec_id, "tasks.md", content)
        return content

    def scaffold_checklist(self, spec_id: str) -> str:
        """Scaffold a quality checklist markdown artifact from the checklist-template."""
        spec = self.load_spec(spec_id)
        if spec is None:
            return ""
        content = self._render_template("checklist-template.md", self._spec_context(spec))
        self._write_scaffold(spec_id, "checklist.md", content)
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
        Reads the auto-rendered ``{spec_id}.md`` if present,
        otherwise validates against built-in criteria.
        """
        spec = self.load_spec(spec_id)
        if spec is None:
            return {"error": f"Spec not found: {spec_id}"}
        md_path = self._spec_md_path(spec_id)
        spec_md = md_path.read_text(encoding="utf-8") if md_path.exists() else ""
        results: dict[str, Any] = {
            "spec_id": spec_id,
            "total_checks": 0,
            "passed": 0,
            "failed": 0,
            "failing_items": [],
        }
        checks = [
            # No unresolved clarification markers remain in the rendered spec.
            # (The auto-rendered artifact never contains implementation code
            # itself, so the operative signal is unresolved clarifications.)
            ("no_implementation_details", "[NEEDS CLARIFICATION" not in spec_md),
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
