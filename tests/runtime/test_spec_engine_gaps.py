"""Gap coverage for runtime/spec/engine.py."""

from __future__ import annotations

import pytest

from runtime.spec.engine import SpecEngine, _render_markdown, _SpecValidator
from runtime.spec.models import (
    DeltaType,
    Spec,
    SpecDelta,
    SpecManifest,
    Task,
)


@pytest.fixture
def engine(tmp_path):
    return SpecEngine(tmp_path / "specs")


class TestValidators:
    def test_delta_added_dup(self, engine):
        engine.init_spec("s1", "t")
        engine.add_requirement("s1", "desc")
        spec = engine.load_spec("s1")
        spec.deltas.append(SpecDelta(requirement_id="REQ-001",
                                     delta_type=DeltaType.ADDED, description="x"))
        errors = _SpecValidator.validate_deltas(spec)
        assert any("already exists" in e for e in errors)

    def test_delta_added_empty_desc(self, engine):
        engine.init_spec("s2", "t")
        spec = engine.load_spec("s2")
        spec.deltas.append(SpecDelta(requirement_id="REQ-099",
                                     delta_type=DeltaType.ADDED, description="  "))
        errors = _SpecValidator.validate_deltas(spec)
        assert any("empty description" in e for e in errors)

    def test_delta_modified_not_found(self, engine):
        engine.init_spec("s3", "t")
        spec = engine.load_spec("s3")
        spec.deltas.append(SpecDelta(requirement_id="REQ-404",
                                     delta_type=DeltaType.MODIFIED, description="x"))
        errors = _SpecValidator.validate_deltas(spec)
        assert any("not found" in e for e in errors)

    def test_delta_modified_empty(self, engine):
        engine.init_spec("s4", "t")
        engine.add_requirement("s4", "orig")
        spec = engine.load_spec("s4")
        spec.deltas.append(SpecDelta(requirement_id="REQ-001",
                                     delta_type=DeltaType.MODIFIED, description=""))
        errors = _SpecValidator.validate_deltas(spec)
        assert any("empty description" in e for e in errors)

    def test_delta_removed_not_found(self, engine):
        engine.init_spec("s5", "t")
        spec = engine.load_spec("s5")
        spec.deltas.append(SpecDelta(requirement_id="REQ-404",
                                     delta_type=DeltaType.REMOVED))
        errors = _SpecValidator.validate_deltas(spec)
        assert any("not found" in e for e in errors)


class TestDrift:
    def test_detect_drift_missing(self, engine):
        out = engine._drift.detect_drift("nope")
        assert "error" in out

    def test_detect_drift_clean(self, engine):
        engine.init_spec("d1", "t")
        out = engine._drift.detect_drift("d1")
        assert out["has_drift"] is False

    def test_drift_modified_json(self, engine):
        engine.init_spec("d2", "t")
        jp = engine._spec_path("d2")
        jp.write_text(jp.read_text() + " ")
        out = engine._drift.detect_drift("d2")
        assert any(i["file"].endswith(".json") for i in out["items"])

    def test_drift_unapplied_deltas(self, engine):
        engine.init_spec("d3", "t")
        engine.add_delta("d3", "REQ-001", DeltaType.ADDED, "new req")
        out = engine._drift.detect_drift("d3")
        assert any(i["type"] == "unapplied_deltas" for i in out["items"])

    def test_phase_regression(self, engine):
        engine.init_spec("d4", "t")
        spec = engine.load_spec("d4")
        spec.state_history = [
            {"to": "plan"}, {"to": "specify"},  # backward move
        ]
        items = engine._drift._check_phase_regression(spec)
        assert items and items[0]["type"] == "phase_regression"

    def test_phase_regression_unknown(self, engine):
        engine.init_spec("d5", "t")
        spec = engine.load_spec("d5")
        spec.state_history = [{"to": "bogus"}, {"to": "plan"}]
        assert engine._drift._check_phase_regression(spec) == []

    def test_manifest_corrupt_baseline(self, engine):
        engine.init_spec("d6", "t")
        mp = engine._manifest_path("d6")
        mp.write_text("{corrupt")
        m = engine._drift.get_manifest("d6")
        assert isinstance(m, SpecManifest)

    def test_is_file_modified_missing_spec(self, engine):
        assert engine._drift.is_file_modified("nope") is True

    def test_is_file_modified_missing_file(self, engine):
        engine.init_spec("d7", "t")
        engine._spec_path("d7").unlink()
        assert engine._drift.is_file_modified("d7") is True

    def test_pagination(self, engine):
        for i in range(5):
            engine.init_spec(f"p{i}", "t")
        out = engine._drift.list_specs_paginated(page=2, page_size=2)
        assert out["total"] == 5 and len(out["items"]) == 2 and out["has_more"]

    def test_pagination_bad_args(self, engine):
        with pytest.raises(ValueError):
            engine._drift.list_specs_paginated(page=0)
        with pytest.raises(ValueError):
            engine._drift.list_specs_paginated(page_size=0)


class TestTaskOps:
    def test_update_invalid_status(self, engine):
        engine.init_spec("t1", "t")
        with pytest.raises(ValueError):
            engine.update_task_status("t1", "TASK-001", "bogus")

    def test_update_task_verified_flag(self, engine):
        engine.init_spec("t2", "t")
        # drive to tasks phase
        engine.add_requirement("t2", "r")
        engine.advance("t2")
        engine.set_plan("t2", {"a": 1})
        engine.advance("t2")
        engine.add_task("t2", "task")
        engine.verify_task("t2", "TASK-001", "evidence")
        spec = engine.load_spec("t2")
        assert spec.tasks[0].status == "done" and spec.tasks[0].verified

    def test_update_done_unverified(self, engine):
        engine.init_spec("t3", "t")
        engine.add_requirement("t3", "r")
        engine.advance("t3")
        engine.set_plan("t3", {"a": 1})
        engine.advance("t3")
        engine.add_task("t3", "task")
        engine.update_task_status("t3", "TASK-001", "done")
        spec = engine.load_spec("t3")
        assert spec.tasks[0].status == "done" and not spec.tasks[0].verified

    def test_verify_task_missing_spec(self, engine):
        assert engine.verify_task("nope", "TASK-001", "e") is False

    def test_verify_task_missing_task(self, engine):
        engine.init_spec("t4", "t")
        assert engine.verify_task("t4", "TASK-404", "e") is False

    def test_update_task_missing_task(self, engine):
        engine.init_spec("t5", "t")
        assert engine.update_task_status("t5", "TASK-404", "done") is False


class TestNextId:
    def test_max_suffix(self, engine):
        nid = engine._next_id("x", "REQ", ["REQ-001", "REQ-007", "REQ-003"])
        assert nid == "REQ-008"

    def test_collision_skip(self, engine):
        nid = engine._next_id("x", "TASK", ["TASK-002", "TASK-001"])
        assert nid == "TASK-003"

    def test_malformed_ignored(self, engine):
        nid = engine._next_id("x", "REQ", ["REQ-abc"])
        assert nid == "REQ-001"


class TestDeltas:
    def test_apply_added(self, engine):
        engine.init_spec("a1", "t")
        engine.add_delta("a1", "REQ-001", DeltaType.ADDED, "new req")
        n = engine.apply_deltas("a1")
        assert n == 1
        spec = engine.load_spec("a1")
        assert spec.requirements[0].description == "new req"

    def test_apply_modified(self, engine):
        engine.init_spec("a2", "t")
        engine.add_requirement("a2", "orig")
        engine.add_delta("a2", "REQ-001", DeltaType.MODIFIED, "changed")
        engine.apply_deltas("a2")
        spec = engine.load_spec("a2")
        assert spec.requirements[0].description == "changed"

    def test_apply_removed(self, engine):
        engine.init_spec("a3", "t")
        engine.add_requirement("a3", "r1")
        engine.add_delta("a3", "REQ-001", DeltaType.REMOVED)
        engine.apply_deltas("a3")
        spec = engine.load_spec("a3")
        assert spec.requirements == []

    def test_apply_invalid_delta(self, engine):
        engine.init_spec("a4", "t")
        engine.add_delta("a4", "REQ-404", DeltaType.MODIFIED, "x")
        with pytest.raises(ValueError):
            engine.apply_deltas("a4")

    def test_add_delta_missing_spec(self, engine):
        with pytest.raises(ValueError):
            engine.add_delta("nope", "R", DeltaType.ADDED)

    def test_apply_deltas_missing_spec(self, engine):
        with pytest.raises(ValueError):
            engine.apply_deltas("nope")


class TestRenderMarkdown:
    def test_all_sections(self, engine):
        engine.init_spec("m1", "T", description="desc", constitution="cons")
        engine.add_requirement("m1", "req", user_story="story")
        engine.advance("m1")
        engine.set_plan("m1", {"k": "v"})
        engine.advance("m1")
        engine.add_task("m1", "task", depends_on=[], estimate_hours=2)
        spec = engine.load_spec("m1")
        md = _render_markdown(spec)
        assert "## Description" in md and "## Constitution" in md
        assert "## Plan" in md and "## Tasks" in md
        assert "As a user" in md and "2h" in md

    def test_task_statuses_render(self, engine):
        spec = Spec(id="x", title="t", created_at="", updated_at="")
        spec.tasks = [
            Task(id="T-1", description="a", status="in_progress"),
            Task(id="T-2", description="b", status="done"),
            Task(id="T-3", description="c", status="blocked"),
        ]
        md = _render_markdown(spec)
        assert "[~]" in md and "[x]" in md and "[!]" in md

    def test_manifest_write(self, engine):
        engine.init_spec("mw", "t")
        assert engine._manifest_path("mw").exists()

    def test_load_corrupt_spec(self, engine):
        engine.init_spec("c1", "t")
        engine._spec_path("c1").write_text("{bad json")
        assert engine.load_spec("c1") is None
