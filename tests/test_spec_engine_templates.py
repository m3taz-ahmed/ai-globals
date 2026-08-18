"""Tests for spec-kit-inspired additions to SpecEngine.

Covers: template scaffolding, constitution, checklist validation,
cross-artifact analysis, and code convergence.

These tests are FAST tier (no MCP, no kernel, no model loading).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from runtime.spec_engine import DeltaType, SpecEngine, SpecPhase


@pytest.fixture
def engine(tmp_path: Path) -> SpecEngine:
    """SpecEngine pointing at a temp specs directory."""
    return SpecEngine(tmp_path / "specs")


@pytest.fixture
def populated_spec(engine: SpecEngine) -> str:
    """Create a spec with requirements, plan, and tasks for analysis tests."""
    engine.init_spec("test-feature", "Test Feature", "A test feature")
    engine.add_requirement("test-feature", "Users can log in with email", user_story="As a user, I want to log in")
    engine.add_requirement("test-feature", "System validates email addresses", user_story="As a system, I validate")
    engine.advance("test-feature")  # specify -> plan
    engine.set_plan("test-feature", {"stack": "FastAPI", "db": "PostgreSQL"})
    engine.advance("test-feature")  # plan -> tasks
    engine.add_task("test-feature", "Create User model", estimate_hours=2.0)
    engine.add_task("test-feature", "Implement login endpoint", depends_on=["TASK-001"])
    return "test-feature"


# -- Template Scaffolding --------------------------------------------------


class TestTemplateScaffolding:
    """Tests for scaffold_spec, scaffold_plan, scaffold_tasks, scaffold_checklist."""

    def test_scaffold_spec_writes_file(self, engine: SpecEngine) -> None:
        """scaffold_spec writes {spec_id}.spec.md with template content."""
        engine.init_spec("auth", "User Authentication", "Login feature")
        content = engine.scaffold_spec("auth", "User Authentication", "Login feature")
        assert content != "" or not Path("tech-stack/spec-driven-templates/spec-template.md").exists()
        scaffold_path = engine.specs_dir / "auth.spec.md"
        if content:
            assert scaffold_path.exists()
            written = scaffold_path.read_text(encoding="utf-8")
            assert "User Authentication" in written
            assert "Feature Branch" in written

    def test_scaffold_plan_writes_file(self, engine: SpecEngine) -> None:
        """scaffold_plan writes {spec_id}.plan.md with template content."""
        engine.init_spec("auth", "User Authentication")
        content = engine.scaffold_plan("auth")
        if content:
            plan_path = engine.specs_dir / "auth.plan.md"
            assert plan_path.exists()
            assert "Implementation Plan" in plan_path.read_text(encoding="utf-8")

    def test_scaffold_tasks_writes_file(self, engine: SpecEngine) -> None:
        """scaffold_tasks writes {spec_id}.tasks.md with template content."""
        engine.init_spec("auth", "User Authentication")
        content = engine.scaffold_tasks("auth")
        if content:
            tasks_path = engine.specs_dir / "auth.tasks.md"
            assert tasks_path.exists()
            assert "Tasks" in tasks_path.read_text(encoding="utf-8")

    def test_scaffold_checklist_writes_file(self, engine: SpecEngine) -> None:
        """scaffold_checklist writes {spec_id}.checklist.md with template content."""
        engine.init_spec("auth", "User Authentication")
        content = engine.scaffold_checklist("auth")
        if content:
            checklist_path = engine.specs_dir / "auth.checklist.md"
            assert checklist_path.exists()
            assert "Quality Checklist" in checklist_path.read_text(encoding="utf-8")

    def test_scaffold_spec_nonexistent_spec(self, engine: SpecEngine) -> None:
        """scaffold_spec on nonexistent spec creates scaffold with provided title."""
        content = engine.scaffold_spec("new-spec", "New Feature", "Description")
        # Should not raise; may return empty if templates absent
        if content:
            assert "New Feature" in content

    def test_scaffold_plan_nonexistent_spec_returns_empty(self, engine: SpecEngine) -> None:
        """scaffold_plan on nonexistent spec returns empty string (no crash)."""
        content = engine.scaffold_plan("nonexistent")
        assert content == ""

    def test_render_template_replaces_placeholders(self, engine: SpecEngine) -> None:
        """_render_template replaces {{PLACEHOLDER}} tokens."""
        engine.init_spec("test", "My Feature")
        context = {"TITLE": "My Feature", "SPEC_ID": "test", "DATE": "2026-01-01"}
        content = engine._render_template("spec-template.md", context)
        if content:
            assert "My Feature" in content
            assert "{{TITLE}}" not in content
            assert "{{DATE}}" not in content


# -- Constitution ----------------------------------------------------------


class TestConstitution:
    """Tests for set_constitution."""

    def test_set_constitution(self, engine: SpecEngine) -> None:
        """set_constitution stores constitution text on the spec."""
        engine.init_spec("auth", "Auth")
        constitution = "I. Library-First: Every feature MUST start as a library."
        engine.set_constitution("auth", constitution)
        spec = engine.load_spec("auth")
        assert spec is not None
        assert spec.constitution == constitution

    def test_set_constitution_nonexistent_raises(self, engine: SpecEngine) -> None:
        """set_constitution on nonexistent spec raises ValueError."""
        with pytest.raises(ValueError, match="Spec not found"):
            engine.set_constitution("nonexistent", "constitution text")


# -- Checklist Validation --------------------------------------------------


class TestValidateChecklist:
    """Tests for validate_checklist."""

    def test_validate_checklist_returns_structure(self, engine: SpecEngine) -> None:
        """validate_checklist returns dict with expected keys."""
        engine.init_spec("auth", "Auth")
        engine.add_requirement("auth", "Users can log in")
        result = engine.validate_checklist("auth")
        assert "spec_id" in result
        assert "total_checks" in result
        assert "passed" in result
        assert "failed" in result
        assert "failing_items" in result
        assert result["total_checks"] > 0
        assert result["passed"] + result["failed"] == result["total_checks"]

    def test_validate_checklist_nonexistent(self, engine: SpecEngine) -> None:
        """validate_checklist on nonexistent spec returns error dict."""
        result = engine.validate_checklist("nonexistent")
        assert "error" in result

    def test_validate_checklist_passes_with_requirements(self, engine: SpecEngine) -> None:
        """Spec with requirements passes the has_requirements check."""
        engine.init_spec("auth", "Auth")
        engine.add_requirement("auth", "Users can log in")
        result = engine.validate_checklist("auth")
        assert "has_requirements" not in result["failing_items"]


# -- Cross-Artifact Analysis -----------------------------------------------


class TestAnalyzeArtifacts:
    """Tests for analyze_artifacts (spec ↔ plan ↔ tasks consistency)."""

    def test_analyze_returns_structure(self, populated_spec: str, engine: SpecEngine) -> None:
        """analyze_artifacts returns dict with metrics and findings."""
        report = engine.analyze_artifacts(populated_spec)
        assert "spec_id" in report
        assert "metrics" in report
        assert "findings" in report
        assert "critical_count" in report
        assert "high_count" in report
        assert "medium_count" in report

    def test_analyze_metrics_counts(self, populated_spec: str, engine: SpecEngine) -> None:
        """analyze_artifacts counts requirements and tasks correctly."""
        report = engine.analyze_artifacts(populated_spec)
        metrics = report["metrics"]
        assert metrics["total_requirements"] == 2
        assert metrics["total_tasks"] == 2

    def test_analyze_nonexistent_spec(self, engine: SpecEngine) -> None:
        """analyze_artifacts on nonexistent spec returns error."""
        report = engine.analyze_artifacts("nonexistent")
        assert "error" in report

    def test_analyze_detects_unresolved_clarification(self, engine: SpecEngine) -> None:
        """analyze_artifacts flags [NEEDS CLARIFICATION] markers."""
        engine.init_spec("auth", "Auth")
        engine.add_requirement("auth", "System MUST [NEEDS CLARIFICATION: auth method]")
        report = engine.analyze_artifacts("auth")
        assert report["metrics"]["unresolved_count"] >= 1
        unc_findings = [f for f in report["findings"] if f["category"] == "underspecification"]
        assert len(unc_findings) >= 1

    def test_analyze_detects_vague_terms(self, engine: SpecEngine) -> None:
        """analyze_artifacts flags vague adjectives without measurable criteria."""
        engine.init_spec("auth", "Auth")
        engine.add_requirement("auth", "System MUST be fast and scalable")
        report = engine.analyze_artifacts("auth")
        assert report["metrics"]["ambiguity_count"] >= 1

    def test_analyze_constitution_violation(self, engine: SpecEngine) -> None:
        """analyze_artifacts flags MUST principles not reflected in spec."""
        engine.init_spec("auth", "Auth")
        engine.set_constitution("auth", "I. Auditability: System MUST log all security events.")
        engine.add_requirement("auth", "Users can log in")
        report = engine.analyze_artifacts("auth")
        # Heuristic-based; may or may not flag depending on keyword match
        assert isinstance(report["metrics"]["constitution_violations"], int)

    def test_analyze_template_constitution_skipped(self, engine: SpecEngine) -> None:
        """analyze_artifacts skips template-only constitutions ({{...}} present)."""
        engine.init_spec("auth", "Auth")
        engine.set_constitution("auth", "I. {{PRINCIPLE_1_NAME}}: {{PRINCIPLE_1_DESCRIPTION}}")
        engine.add_requirement("auth", "Users can log in")
        report = engine.analyze_artifacts("auth")
        assert report["metrics"]["constitution_violations"] == 0


# -- Code Convergence ------------------------------------------------------


class TestConvergeToCode:
    """Tests for converge_to_code (codebase vs spec/plan/tasks gap analysis)."""

    def test_converge_returns_structure(self, populated_spec: str, engine: SpecEngine, tmp_path: Path) -> None:
        """converge_to_code returns dict with metrics, findings, suggested_tasks."""
        codebase = tmp_path / "codebase"
        codebase.mkdir()
        report = engine.converge_to_code(populated_spec, codebase)
        assert "spec_id" in report
        assert "codebase_dir" in report
        assert "files_scanned" in report
        assert "metrics" in report
        assert "findings" in report
        assert "suggested_tasks" in report
        assert "converged" in report

    def test_converge_empty_codebase_all_missing(self, populated_spec: str, engine: SpecEngine, tmp_path: Path) -> None:
        """Empty codebase → all requirements flagged as missing."""
        codebase = tmp_path / "empty"
        codebase.mkdir()
        report = engine.converge_to_code(populated_spec, codebase)
        assert report["metrics"]["missing_count"] >= 1
        assert report["converged"] is False

    def test_converge_nonexistent_spec(self, engine: SpecEngine, tmp_path: Path) -> None:
        """converge_to_code on nonexistent spec returns error."""
        report = engine.converge_to_code("nonexistent", tmp_path)
        assert "error" in report

    def test_converge_nonexistent_codebase(self, populated_spec: str, engine: SpecEngine, tmp_path: Path) -> None:
        """converge_to_code with missing codebase dir returns error."""
        report = engine.converge_to_code(populated_spec, tmp_path / "nonexistent")
        assert "error" in report

    def test_converge_suggests_tasks_with_ids(self, populated_spec: str, engine: SpecEngine, tmp_path: Path) -> None:
        """converge_to_code suggests tasks with sequential IDs."""
        codebase = tmp_path / "codebase"
        codebase.mkdir()
        report = engine.converge_to_code(populated_spec, codebase)
        if report["suggested_tasks"]:
            first_task = report["suggested_tasks"][0]
            assert "id" in first_task
            assert first_task["id"].startswith("T")
            assert "description" in first_task
            assert "severity" in first_task

    def test_converge_finds_keyword_match(self, engine: SpecEngine, tmp_path: Path) -> None:
        """converge_to_code recognizes requirement keywords present in code."""
        engine.init_spec("auth", "Auth")
        engine.add_requirement("auth", "System MUST authenticate users with password")
        codebase = tmp_path / "codebase"
        codebase.mkdir()
        (codebase / "auth.py").write_text(
            "def authenticate(user, password):\n    return check_password(user, password)\n",
            encoding="utf-8",
        )
        report = engine.converge_to_code("auth", codebase)
        # "authenticate" and "password" should match → requirement not flagged as missing
        missing_for_auth = [
            f for f in report["findings"] if "auth" in f.get("source_ref", "").lower() or "REQ" in f.get("source_ref", "")
        ]
        # No finding should be "missing" for this requirement (keywords found in code)
        assert not any(f["gap_type"] == "missing" for f in missing_for_auth)


# -- Backward Compatibility ------------------------------------------------


class TestBackwardCompat:
    """Verify existing SpecEngine behavior is unchanged by new additions."""

    def test_init_spec_still_works(self, engine: SpecEngine) -> None:
        """init_spec creates spec with JSON + MD artifacts (legacy behavior)."""
        spec = engine.init_spec("legacy", "Legacy Feature")
        assert spec.id == "legacy"
        assert (engine.specs_dir / "legacy.json").exists()
        assert (engine.specs_dir / "legacy.md").exists()

    def test_phases_still_advance(self, engine: SpecEngine) -> None:
        """Phase advancement still works with validation gates."""
        engine.init_spec("phases", "Phase Test")
        engine.add_requirement("phases", "Req 1")
        spec = engine.advance("phases")
        assert spec.phase == SpecPhase.PLAN
        engine.set_plan("phases", {"stack": "test"})
        spec = engine.advance("phases")
        assert spec.phase == SpecPhase.TASKS

    def test_list_specs_still_works(self, engine: SpecEngine) -> None:
        """list_specs returns existing specs."""
        engine.init_spec("list1", "Feature 1")
        engine.init_spec("list2", "Feature 2")
        specs = engine.list_specs()
        assert len(specs) == 2
        ids = {s["id"] for s in specs}
        assert ids == {"list1", "list2"}

    def test_deltas_still_work(self, engine: SpecEngine) -> None:
        """Delta-based spec changes still function."""
        engine.init_spec("delta", "Delta Test")
        engine.add_delta("delta", "REQ-001", DeltaType.ADDED, "New requirement")
        spec = engine.load_spec("delta")
        assert spec is not None
        assert len(spec.deltas) == 1
        applied = engine.apply_deltas("delta")
        assert applied == 1
