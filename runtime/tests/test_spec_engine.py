"""Tests for runtime/spec_engine.py — spec-driven development engine."""

from __future__ import annotations

from pathlib import Path

import pytest

from runtime.spec_engine import (
    Requirement,
    Spec,
    SpecEngine,
    SpecPhase,
    Task,
)


@pytest.fixture
def engine(tmp_path: Path) -> SpecEngine:
    """Create a spec engine in a temp directory."""
    return SpecEngine(tmp_path / "specs")


class TestSpecPhase:
    """Tests for SpecPhase enum."""

    def test_phase_values(self) -> None:
        assert SpecPhase.SPECIFY.value == "specify"
        assert SpecPhase.PLAN.value == "plan"
        assert SpecPhase.TASKS.value == "tasks"
        assert SpecPhase.IMPLEMENT.value == "implement"
        assert SpecPhase.DONE.value == "done"


class TestRequirement:
    """Tests for Requirement."""

    def test_defaults(self) -> None:
        r = Requirement(id="REQ-001", description="test")
        assert r.priority == "must"
        assert r.user_story == ""


class TestTask:
    """Tests for Task."""

    def test_defaults(self) -> None:
        t = Task(id="TASK-001", description="test")
        assert t.status == "pending"
        assert t.depends_on == []
        assert t.estimate_hours == 0.0


class TestSpec:
    """Tests for Spec."""

    def test_to_dict_roundtrip(self) -> None:
        spec = Spec(id="test", title="Test Spec", description="A test")
        spec.requirements.append(Requirement(id="REQ-001", description="req"))
        spec.tasks.append(Task(id="TASK-001", description="task"))
        d = spec.to_dict()
        restored = Spec.from_dict(d)
        assert restored.id == "test"
        assert restored.title == "Test Spec"
        assert len(restored.requirements) == 1
        assert len(restored.tasks) == 1

    def test_to_dict_empty(self) -> None:
        spec = Spec(id="test", title="Test")
        d = spec.to_dict()
        assert d["requirements"] == []
        assert d["tasks"] == []
        assert d["plan"] == {}


class TestSpecEngine:
    """Tests for SpecEngine."""

    def test_init_spec(self, engine: SpecEngine) -> None:
        spec = engine.init_spec("auth", "User Authentication", "Login system")
        assert spec.id == "auth"
        assert spec.title == "User Authentication"
        assert spec.phase == SpecPhase.SPECIFY
        assert engine._spec_path("auth").exists()

    def test_init_spec_duplicate(self, engine: SpecEngine) -> None:
        engine.init_spec("auth", "Auth")
        with pytest.raises(ValueError, match="already exists"):
            engine.init_spec("auth", "Auth")

    def test_load_spec(self, engine: SpecEngine) -> None:
        engine.init_spec("auth", "Auth")
        spec = engine.load_spec("auth")
        assert spec is not None
        assert spec.id == "auth"

    def test_load_spec_nonexistent(self, engine: SpecEngine) -> None:
        assert engine.load_spec("nonexistent") is None

    def test_add_requirement(self, engine: SpecEngine) -> None:
        engine.init_spec("auth", "Auth")
        req = engine.add_requirement("auth", "Users can log in", priority="must")
        assert req.id == "REQ-001"
        assert req.priority == "must"
        spec = engine.load_spec("auth")
        assert len(spec.requirements) == 1

    def test_add_requirement_wrong_phase(self, engine: SpecEngine) -> None:
        engine.init_spec("auth", "Auth")
        engine.add_requirement("auth", "req1")
        engine.advance("auth")  # -> plan
        with pytest.raises(ValueError, match="Cannot add requirements"):
            engine.add_requirement("auth", "req2")

    def test_add_requirement_nonexistent_spec(self, engine: SpecEngine) -> None:
        with pytest.raises(ValueError, match="not found"):
            engine.add_requirement("nonexistent", "req")

    def test_set_plan(self, engine: SpecEngine) -> None:
        engine.init_spec("auth", "Auth")
        engine.add_requirement("auth", "req1")
        engine.advance("auth")  # -> plan
        engine.set_plan("auth", {"stack": "FastAPI", "db": "PostgreSQL"})
        spec = engine.load_spec("auth")
        assert spec.plan["stack"] == "FastAPI"

    def test_set_plan_wrong_phase(self, engine: SpecEngine) -> None:
        engine.init_spec("auth", "Auth")
        with pytest.raises(ValueError, match="Cannot set plan"):
            engine.set_plan("auth", {"stack": "x"})

    def test_add_task(self, engine: SpecEngine) -> None:
        engine.init_spec("auth", "Auth")
        engine.add_requirement("auth", "req1")
        engine.advance("auth")  # -> plan
        engine.set_plan("auth", {"stack": "FastAPI"})
        engine.advance("auth")  # -> tasks
        task = engine.add_task("auth", "Create User model", estimate_hours=2.0)
        assert task.id == "TASK-001"
        assert task.estimate_hours == 2.0

    def test_add_task_wrong_phase(self, engine: SpecEngine) -> None:
        engine.init_spec("auth", "Auth")
        with pytest.raises(ValueError, match="Cannot add tasks"):
            engine.add_task("auth", "task1")

    def test_update_task_status(self, engine: SpecEngine) -> None:
        engine.init_spec("auth", "Auth")
        engine.add_requirement("auth", "req1")
        engine.advance("auth")
        engine.set_plan("auth", {"stack": "x"})
        engine.advance("auth")
        engine.add_task("auth", "task1")
        result = engine.update_task_status("auth", "TASK-001", "done")
        assert result is True
        spec = engine.load_spec("auth")
        assert spec.tasks[0].status == "done"

    def test_update_task_status_nonexistent(self, engine: SpecEngine) -> None:
        engine.init_spec("auth", "Auth")
        assert engine.update_task_status("auth", "TASK-999", "done") is False

    def test_advance_specify_to_plan(self, engine: SpecEngine) -> None:
        engine.init_spec("auth", "Auth")
        engine.add_requirement("auth", "req1")
        spec = engine.advance("auth")
        assert spec.phase == SpecPhase.PLAN

    def test_advance_no_requirements_fails(self, engine: SpecEngine) -> None:
        engine.init_spec("auth", "Auth")
        with pytest.raises(ValueError, match="no requirements"):
            engine.advance("auth")

    def test_advance_plan_to_tasks(self, engine: SpecEngine) -> None:
        engine.init_spec("auth", "Auth")
        engine.add_requirement("auth", "req1")
        engine.advance("auth")
        engine.set_plan("auth", {"stack": "x"})
        spec = engine.advance("auth")
        assert spec.phase == SpecPhase.TASKS

    def test_advance_no_plan_fails(self, engine: SpecEngine) -> None:
        engine.init_spec("auth", "Auth")
        engine.add_requirement("auth", "req1")
        engine.advance("auth")
        with pytest.raises(ValueError, match="no plan"):
            engine.advance("auth")

    def test_advance_tasks_to_implement(self, engine: SpecEngine) -> None:
        engine.init_spec("auth", "Auth")
        engine.add_requirement("auth", "req1")
        engine.advance("auth")
        engine.set_plan("auth", {"stack": "x"})
        engine.advance("auth")
        engine.add_task("auth", "task1")
        spec = engine.advance("auth")
        assert spec.phase == SpecPhase.IMPLEMENT

    def test_advance_no_tasks_fails(self, engine: SpecEngine) -> None:
        engine.init_spec("auth", "Auth")
        engine.add_requirement("auth", "req1")
        engine.advance("auth")
        engine.set_plan("auth", {"stack": "x"})
        engine.advance("auth")
        with pytest.raises(ValueError, match="no tasks"):
            engine.advance("auth")

    def test_advance_implement_to_done(self, engine: SpecEngine) -> None:
        engine.init_spec("auth", "Auth")
        engine.add_requirement("auth", "req1")
        engine.advance("auth")
        engine.set_plan("auth", {"stack": "x"})
        engine.advance("auth")
        engine.add_task("auth", "task1")
        engine.advance("auth")  # -> implement
        engine.update_task_status("auth", "TASK-001", "done")
        spec = engine.advance("auth")
        assert spec.phase == SpecPhase.DONE

    def test_advance_implement_incomplete_fails(self, engine: SpecEngine) -> None:
        engine.init_spec("auth", "Auth")
        engine.add_requirement("auth", "req1")
        engine.advance("auth")
        engine.set_plan("auth", {"stack": "x"})
        engine.advance("auth")
        engine.add_task("auth", "task1")
        engine.advance("auth")  # -> implement
        with pytest.raises(ValueError, match="not all tasks"):
            engine.advance("auth")

    def test_advance_done_fails(self, engine: SpecEngine) -> None:
        engine.init_spec("auth", "Auth")
        engine.add_requirement("auth", "req1")
        engine.advance("auth")
        engine.set_plan("auth", {"stack": "x"})
        engine.advance("auth")
        engine.add_task("auth", "task1")
        engine.advance("auth")
        engine.update_task_status("auth", "TASK-001", "done")
        engine.advance("auth")  # -> done
        with pytest.raises(ValueError, match="already done"):
            engine.advance("auth")

    def test_can_advance(self, engine: SpecEngine) -> None:
        engine.init_spec("auth", "Auth")
        can, msg = engine.can_advance("auth")
        assert can is False
        assert "No requirements" in msg
        engine.add_requirement("auth", "req1")
        can, msg = engine.can_advance("auth")
        assert can is True

    def test_can_advance_nonexistent(self, engine: SpecEngine) -> None:
        can, _msg = engine.can_advance("nonexistent")
        assert can is False

    def test_list_specs(self, engine: SpecEngine) -> None:
        engine.init_spec("auth", "Auth")
        engine.init_spec("api", "API")
        specs = engine.list_specs()
        assert len(specs) == 2

    def test_list_specs_empty(self, engine: SpecEngine) -> None:
        assert engine.list_specs() == []

    def test_delete_spec(self, engine: SpecEngine) -> None:
        engine.init_spec("auth", "Auth")
        assert engine.delete_spec("auth") is True
        assert engine.load_spec("auth") is None

    def test_delete_spec_nonexistent(self, engine: SpecEngine) -> None:
        assert engine.delete_spec("nonexistent") is False

    def test_markdown_artifact_generated(self, engine: SpecEngine) -> None:
        engine.init_spec("auth", "Auth", "Login system")
        engine.add_requirement("auth", "Users can log in", user_story="As a user...")
        md_path = engine._spec_md_path("auth")
        assert md_path.exists()
        content = md_path.read_text(encoding="utf-8")
        assert "Auth" in content
        assert "Users can log in" in content
