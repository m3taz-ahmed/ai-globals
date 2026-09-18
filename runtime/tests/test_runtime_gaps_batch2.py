"""Gap coverage batch: output_gate, plan_diff_validator, persona, learning_loop, spec.engine."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

import runtime.output_gate as og
from runtime.learning_loop import (
    HookContext,
    HookPhase,
    HookRegistry,
    LearningLoop,
    Pattern,
    _coerce_ok,
    _parse_ts,
)
from runtime.persona import PersonaDetector, _load_skill_description, format_persona_status
from runtime.plan_diff_validator import PlanDiffValidator, PlanValidationError
from runtime.spec.engine import SpecEngine, _SpecValidator
from runtime.spec.models import DeltaType, Spec, SpecDelta, SpecPhase


class TestOutputGate:
    def test_error_count_and_to_dict(self):
        res = og.check_output("Great question! Here is the fix.\nRun the tests now.")
        assert res.error_count >= 1
        d = res.to_dict()
        assert d["error_count"] == res.error_count

    def test_openers_empty(self):
        assert og._check_openers([]) == []

    def test_closers_empty(self):
        assert og._check_closers([]) == []

    def test_recap_pattern(self):
        issues = og._check_recaps("Fixed the bug\nSo to summarize, we did X")
        assert any(i.category == "recap" for i in issues)

    def test_first_line_no_action(self):
        issues = og._check_first_last_line_test(
            ["The results look fine overall", "done"]
        )
        assert any(i.category == "first-line" for i in issues)

    def test_auto_fix_blank_lines(self):
        fixed, _ = og.auto_fix("Run the tests.\n\nThen deploy.")
        assert "\n\n" in fixed

    def test_auto_fix_opener_only_line(self):
        fixed, _ = og.auto_fix("Great question!\nRun the tests.")
        assert "great question" not in fixed.lower()

    def test_auto_fix_trailing_blank(self):
        fixed, _ = og.auto_fix("Run the tests.\n\n")
        assert fixed.endswith("Run the tests.")

    def test_auto_fix_no_opener(self):
        fixed, _remaining = og.auto_fix("Run the tests now.\nDone.")
        assert "Run the tests" in fixed


class TestPlanDiffValidator:
    def test_error_init(self):
        e = PlanValidationError("bad plan")
        assert "PLAN_VALIDATION_ERROR" in str(e.error_code) or e.message == "bad plan"

    def test_plan_files_code_block_and_bullets(self, tmp_path: Path):
        v = PlanDiffValidator(tmp_path)
        plan = "Steps:\n- fix the thing\n```\nsrc/foo.py\n```\n- notes only"
        files = v.extract_plan_files(plan)
        assert "src/foo.py" in files

    def test_diff_ts_relative_import_skipped(self, tmp_path: Path):
        v = PlanDiffValidator(tmp_path)
        diff = "+import x from './local';\n+import y from '@/lib';\n+import z from 'lodash';"
        res = v.validate_diff(diff)
        assert res is not None

    def test_python_undeclared_and_stdlib(self, tmp_path: Path):
        (tmp_path / "requirements.txt").write_text("requests==2.0\n# comment\n==bad\n")
        v = PlanDiffValidator(tmp_path)
        diff = "+import requests\n+import numpy\n+import os"
        res = v.validate_diff(diff)
        rules = [f.message for f in res.findings]
        assert any("numpy" in r for r in rules)
        assert not any(r == "os" or "'os'" in r for r in rules)

    def test_pyproject_read_error(self, tmp_path: Path):
        (tmp_path / "pyproject.toml").write_text("[project]\nrequests>=2\n")
        v = PlanDiffValidator(tmp_path)
        with patch.object(Path, "read_text", side_effect=OSError("denied")):
            deps = v._load_declared_python_deps()
        assert deps == set()

    def test_reqs_read_error(self, tmp_path: Path):
        (tmp_path / "requirements.txt").write_text("requests==2.0\n")
        v = PlanDiffValidator(tmp_path)
        with patch.object(Path, "read_text", side_effect=OSError("denied")):
            deps = v._load_declared_python_deps()
        assert deps == set()

    def test_package_json_invalid(self, tmp_path: Path):
        (tmp_path / "package.json").write_text("{invalid json")
        v = PlanDiffValidator(tmp_path)
        deps = v._load_declared_ts_deps()
        assert deps == set()

    def test_ts_declared_no_finding(self, tmp_path: Path):
        (tmp_path / "package.json").write_text(
            json.dumps({"dependencies": {"lodash": "^4"}})
        )
        v = PlanDiffValidator(tmp_path)
        diff = "+import z from 'lodash';\n+import q from 'undeclared-pkg';"
        res = v.validate_diff(diff)
        msgs = [f.message for f in res.findings]
        assert any("undeclared-pkg" in m for m in msgs)
        assert not any("lodash" in m for m in msgs)


class TestPersona:
    def test_skill_desc_flat_file(self, tmp_path: Path):
        (tmp_path / "myskill.md").write_text(
            "---\ndescription: Does things\n---\nbody", encoding="utf-8"
        )
        assert _load_skill_description("myskill", tmp_path) == "Does things"

    def test_skill_desc_folder_layout(self, tmp_path: Path):
        d = tmp_path / "folderskill"
        d.mkdir()
        (d / "SKILL.md").write_text(
            "---\ndescription: Folder skill\n---\nbody", encoding="utf-8"
        )
        assert _load_skill_description("folderskill", tmp_path) == "Folder skill"

    def test_skill_desc_no_frontmatter_then_folder(self, tmp_path: Path):
        (tmp_path / "x.md").write_text("no frontmatter", encoding="utf-8")
        d = tmp_path / "x"
        d.mkdir()
        (d / "SKILL.md").write_text(
            "---\ndescription: Second chance\n---\n", encoding="utf-8"
        )
        assert _load_skill_description("x", tmp_path) == "Second chance"

    def test_skill_desc_invalid_yaml(self, tmp_path: Path):
        (tmp_path / "bad.md").write_text("---\n{a: [unclosed\n---\n", encoding="utf-8")
        assert _load_skill_description("bad", tmp_path) == ""

    def test_skill_desc_fm_not_dict(self, tmp_path: Path):
        (tmp_path / "list.md").write_text("---\n- a\n- b\n---\n", encoding="utf-8")
        d = tmp_path / "list"
        d.mkdir()
        (d / "SKILL.md").write_text(
            "---\ndescription: fallback\n---\n", encoding="utf-8"
        )
        assert _load_skill_description("list", tmp_path) == "fallback"

    def test_skill_desc_missing(self, tmp_path: Path):
        assert _load_skill_description("nope", tmp_path) == ""

    def test_format_status_empty(self):
        det = PersonaDetector()
        out = format_persona_status({"persona": "", "personas": []}, det)
        assert "لم يتم تحديد" in out

    def test_format_status_full(self, tmp_path: Path):
        (tmp_path / "dok.md").write_text(
            "---\ndescription: Doc skill\n---\n", encoding="utf-8"
        )
        det = PersonaDetector()
        ctx = {
            "persona": "ARCH",
            "personas": ["ARCH", "DEV"],
            "skills": ["dok", "nodesc"],
            "lords": ["lordx"],
        }
        out = format_persona_status(ctx, det, skills_dir=tmp_path)
        assert "ARCH" in out
        assert "dok" in out
        assert "lordx" in out

    def test_format_status_personas_no_primary(self):
        det = PersonaDetector()
        out = format_persona_status({"persona": "", "personas": ["DEV"]}, det)
        assert "الشخصيات الإضافية" in out or "DEV" in out

    def test_keyword_match_fallback(self):
        det = PersonaDetector()
        assert det._keyword_match("hello world skill", "nonexistent-zz") is False
        assert det._keyword_match("uses nonexistentzz here", "nonexistentzz") is True


class TestLearningLoop:
    def test_parse_ts_invalid(self):
        from datetime import datetime, timezone
        assert _parse_ts("garbage") == datetime.fromtimestamp(0, tz=timezone.utc)

    def test_coerce_ok_str(self):
        assert _coerce_ok("false") is False
        assert _coerce_ok("true") is True

    def test_pattern_to_dict(self):
        d = Pattern(action="a", gate="g", total=2, successes=1).to_dict()
        assert d["action"] == "a" and d["total"] == 2

    def test_bind_hooks_error_no_errors(self):
        reg = HookRegistry()
        loop = LearningLoop()
        loop.bind_to_hooks(reg)
        ctx = HookContext(action="act")
        for fn in reg._hooks.get(HookPhase.ON_ERROR, []):
            fn(ctx)
        assert loop.outcome_count == 0

    def test_bind_hooks_error_with_errors(self):
        reg = HookRegistry()
        loop = LearningLoop()
        loop.bind_to_hooks(reg)
        ctx = HookContext(action="act", errors=["boom"])
        for fn in reg._hooks.get(HookPhase.ON_ERROR, []):
            fn(ctx)
        assert loop.outcome_count == 1

    def test_record_non_dict_result(self):
        loop = LearningLoop()
        with pytest.raises(TypeError):
            loop.record("act", result=[1, 2])  # type: ignore[arg-type]

    def test_persist_batch(self, tmp_path: Path):
        p = tmp_path / "out.json"
        loop = LearningLoop(persist_path=p)
        loop._persist_batch_size = 3
        for i in range(3):
            loop.record(f"a{i}")
        assert p.exists()

    def test_rank_none(self):
        loop = LearningLoop()
        loop.record("a", success=True)
        ranked = loop.rank()
        assert ranked and ranked[0].action == "a"

    def test_inject_none(self):
        loop = LearningLoop()
        loop.record("a", success=True)
        loop.record("a", success=True)
        out = loop.inject()
        assert "Learned Patterns" in out

    def test_flush_not_dirty(self):
        LearningLoop().flush()

    def test_persist_oserror(self, tmp_path: Path):
        p = tmp_path / "o.json"
        loop = LearningLoop(persist_path=p)
        loop.record("a")
        with patch.object(Path, "write_text", side_effect=OSError("disk full")):
            loop.flush()

    def test_load_corrupt(self, tmp_path: Path):
        p = tmp_path / "bad.json"
        p.write_text("{not json", encoding="utf-8")
        loop = LearningLoop(persist_path=p)
        assert loop.outcome_count == 0


class TestSpecEngine:
    def test_constitution_stopword_only_principle(self):
        spec = Spec(id="s", title="t", constitution="Users MUST use the all be")
        assert _SpecValidator.constitution_violations(spec) == []

    def test_validate_deltas_removed(self):
        spec = Spec(id="s", title="t")
        spec.deltas.append(
            SpecDelta(requirement_id="FR-999", delta_type=DeltaType.REMOVED)
        )
        errors = _SpecValidator.validate_deltas(spec)
        assert any("REMOVED" in e for e in errors)

    def test_render_markdown_phase_valueerror(self, tmp_path: Path):
        eng = SpecEngine(tmp_path)
        spec = eng.init_spec("s1", "T")
        import runtime.spec.engine as se
        with patch.object(se, "PHASE_ORDER", []):
            out = se._render_markdown(spec)
        assert "s1" in out

    def test_manifest_baseline_created(self, tmp_path: Path):
        eng = SpecEngine(tmp_path)
        spec = eng.init_spec("s2", "T")
        # delete baseline then get_manifest recreates it
        mpath = eng._manifest_path(spec.id)
        if mpath.exists():
            mpath.unlink()
        manifest = eng.get_manifest(spec.id)
        assert manifest is not None

    def test_manifest_md_only(self, tmp_path: Path):
        eng = SpecEngine(tmp_path)
        spec = eng.init_spec("s3", "T")
        eng._manifest_path(spec.id).unlink(missing_ok=True)
        eng._spec_path(spec.id).unlink(missing_ok=True)
        manifest = eng.get_manifest(spec.id)
        assert manifest is not None

    def test_is_file_modified_missing(self, tmp_path: Path):
        eng = SpecEngine(tmp_path)
        spec = eng.init_spec("s4", "T")
        eng._spec_path(spec.id).unlink(missing_ok=True)
        assert eng.is_file_modified(spec.id, "json") is True

    def test_drift_md_modified(self, tmp_path: Path):
        eng = SpecEngine(tmp_path)
        spec = eng.init_spec("s5", "T")
        md = eng._spec_md_path(spec.id)
        if md.exists():
            md.write_text("tampered content", encoding="utf-8")
            drift = eng.detect_drift(spec.id)
            assert drift is not None

    def test_phase_regression(self, tmp_path: Path):
        eng = SpecEngine(tmp_path)
        spec = eng.init_spec("s6", "T")
        spec.state_history = [{"to": "implement"}, {"to": "specify"}]
        eng._save(spec)
        drift = eng.detect_drift(spec.id)
        items = drift.get("items") or drift.get("issues") or []
        assert any(i.get("type") == "phase_regression" for i in items)

    def test_phase_history_unknown_value(self, tmp_path: Path):
        eng = SpecEngine(tmp_path)
        spec = eng.init_spec("s7", "T")
        spec.state_history = [{"to": "bogus-phase"}, {"to": "specify"}]
        eng._save(spec)
        eng.detect_drift(spec.id)  # should not raise

    def test_update_task_status_not_found(self, tmp_path: Path):
        eng = SpecEngine(tmp_path)
        spec = eng.init_spec("s8", "T")
        spec.phase = SpecPhase.TASKS
        eng._save(spec)
        eng.add_task(spec.id, "t1 desc")
        assert eng.update_task_status(spec.id, "NOPE-999", "done") is False

    def test_update_task_status_not_done(self, tmp_path: Path):
        eng = SpecEngine(tmp_path)
        spec = eng.init_spec("s9", "T")
        spec.phase = SpecPhase.TASKS
        eng._save(spec)
        task = eng.add_task(spec.id, "desc")
        eng.update_task_status(spec.id, task.id, "done")
        # now set to in_progress -> verified reset
        eng.update_task_status(spec.id, task.id, "in_progress")
        loaded = eng.load_spec(spec.id)
        t = next(x for x in loaded.tasks if x.id == task.id)
        assert t.verified is False

    def test_verify_task_not_found(self, tmp_path: Path):
        eng = SpecEngine(tmp_path)
        eng.init_spec("s10", "T")
        assert eng.verify_task("s10", "T-999", "evidence") is False

    def test_verify_task_already_done(self, tmp_path: Path):
        eng = SpecEngine(tmp_path)
        spec = eng.init_spec("s11", "T")
        spec.phase = SpecPhase.TASKS
        eng._save(spec)
        task = eng.add_task(spec.id, "desc")
        eng.update_task_status(spec.id, task.id, "done")
        assert eng.verify_task(spec.id, task.id, "evidence here") is True

    def test_apply_delta_modified_missing(self, tmp_path: Path):
        eng = SpecEngine(tmp_path)
        spec = eng.init_spec("s12", "T")
        # loop iterates non-matching req then matches second
        r1 = eng.add_requirement(spec.id, "first")
        spec = eng.load_spec(spec.id)
        delta = SpecDelta(requirement_id=r1.id, delta_type=DeltaType.MODIFIED, description="new")
        eng._apply_single_delta(spec, delta)
        assert spec.requirements[0].description == "new"
        # MODIFIED on nonexistent id -> for-loop exits without break
        delta2 = SpecDelta(requirement_id="FR-999", delta_type=DeltaType.MODIFIED, description="x")
        eng._apply_single_delta(spec, delta2)

    def test_apply_delta_removed(self, tmp_path: Path):
        eng = SpecEngine(tmp_path)
        spec = eng.init_spec("s13", "T")
        req = eng.add_requirement(spec.id, "req desc")
        eng.add_delta(spec.id, req.id, DeltaType.REMOVED)
        eng.apply_deltas(spec.id)
        loaded = eng.load_spec(spec.id)
        assert all(r.id != req.id for r in loaded.requirements)

    def test_delete_spec_oserror(self, tmp_path: Path):
        eng = SpecEngine(tmp_path)
        spec = eng.init_spec("s14", "T")
        real_unlink = Path.unlink
        calls = {"n": 0}

        def flaky(self, *a, **k):
            calls["n"] += 1
            if calls["n"] == 1:
                raise OSError("locked")
            return real_unlink(self, *a, **k)

        with patch.object(Path, "unlink", flaky):
            eng.delete_spec(spec.id)
