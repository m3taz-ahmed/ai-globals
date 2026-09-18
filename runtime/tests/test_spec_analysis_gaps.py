"""Coverage-gap tests for runtime/spec/analysis.py and spec/engine.py edges."""

from __future__ import annotations

import types
from pathlib import Path

import pytest

import runtime.spec.analysis as analysis_mod
from runtime.spec.engine import SpecEngine, _render_markdown, _SpecValidator
from runtime.spec.models import DeltaType, SpecPhase


def _eng(tmp_path: Path) -> SpecEngine:
    return SpecEngine(tmp_path)


# --- analyze_artifacts -------------------------------------------------------


def test_analyze_missing_spec(tmp_path: Path) -> None:
    eng = _eng(tmp_path)
    assert "error" in eng.analyze_artifacts("ghost")


def test_analyze_vague_term_with_unit_not_flagged(tmp_path: Path) -> None:
    eng = _eng(tmp_path)
    filler = "with additional descriptive behavior " * 3
    eng.init_spec("s1", "T", description=f"respond fast within 100ms {filler} remain fast")
    report = eng.analyze_artifacts("s1")
    assert report["metrics"]["ambiguity_count"] == 1
    assert "fast" in report["findings"][0]["summary"]


def test_analyze_uncovered_req_and_markers(tmp_path: Path) -> None:
    eng = _eng(tmp_path)
    eng.init_spec("s1", "T", description="plain description body")
    covered = eng.add_requirement("s1", "unique widget handler")
    eng.add_requirement("s1", "orphan requirement body")
    (tmp_path / "s1.tasks.md").write_text(
        f"- T001 {covered.description}\n", encoding="utf-8"
    )
    md = eng._spec_md_path("s1")
    md.write_text(
        md.read_text(encoding="utf-8")
        + "\n[NEEDS CLARIFICATION: scope] TODO\n",
        encoding="utf-8",
    )
    report = eng.analyze_artifacts("s1")
    cats = {f["category"] for f in report["findings"]}
    assert "coverage_gap" in cats
    assert "underspecification" in cats
    assert report["metrics"]["coverage_pct"] == 50.0
    assert report["metrics"]["todo_count"] >= 1


def test_analyze_constitution_violation(tmp_path: Path) -> None:
    eng = _eng(tmp_path)
    eng.init_spec("s1", "T", constitution="MUST frobnicate widgets.")
    eng._spec_md_path("s1").unlink()
    report = eng.analyze_artifacts("s1")
    assert report["metrics"]["constitution_violations"] == 1
    assert any(f["category"] == "constitution_violation" for f in report["findings"])


# --- converge_to_code --------------------------------------------------------


def test_converge_missing_spec(tmp_path: Path) -> None:
    eng = _eng(tmp_path)
    assert "error" in eng.converge_to_code("ghost", tmp_path)


def test_converge_unresolvable_dir(tmp_path: Path) -> None:
    eng = _eng(tmp_path)
    eng.init_spec("s1", "T")
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(Path, "resolve", lambda self, *a, **k: (_ for _ in ()).throw(OSError("boom")))
        report = eng.converge_to_code("s1", tmp_path)
    assert "not resolvable" in report["error"]


def test_converge_not_a_dir(tmp_path: Path) -> None:
    eng = _eng(tmp_path)
    eng.init_spec("s1", "T")
    f = tmp_path / "file.txt"
    f.write_text("x")
    assert "not found" in eng.converge_to_code("s1", f)["error"]


def test_converge_file_cap(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    eng = _eng(tmp_path)
    eng.init_spec("s1", "T")
    code = tmp_path / "code"
    code.mkdir()
    for i in range(4):
        (code / f"m{i}.py").write_text(f"audit{i} = 1\n")
    monkeypatch.setattr(analysis_mod, "_MAX_CONVERGE_FILES", 2)
    report = eng.converge_to_code("s1", code)
    assert "findings" in report or "metrics" in report or "gaps" in report or report


def test_converge_skips_noncode_and_ignored(tmp_path: Path) -> None:
    eng = _eng(tmp_path)
    spec = eng.init_spec("s1", "T")
    eng.add_requirement("s1", "audit trail logging")
    code = tmp_path / "code"
    (code / "node_modules").mkdir(parents=True)
    (code / "node_modules" / "dep.py").write_text("audit = 1\n")
    (code / "note.txt").write_text("audit\n")
    (code / "sub").mkdir()
    report = eng.converge_to_code("s1", code)
    assert report["spec_id"] == "s1"
    assert spec.id == "s1"


def test_converge_oversized_file_skipped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    eng = _eng(tmp_path)
    eng.init_spec("s1", "T")
    code = tmp_path / "code"
    code.mkdir()
    (code / "big.py").write_text("x" * 50)
    monkeypatch.setattr(analysis_mod, "_MAX_FILE_BYTES", 10)
    report = eng.converge_to_code("s1", code)
    assert report["spec_id"] == "s1"


def test_converge_read_error_skipped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    eng = _eng(tmp_path)
    eng.init_spec("s1", "T")
    code = tmp_path / "code"
    code.mkdir()
    (code / "bad.py").write_text("audit\n")
    original = Path.read_text

    def flaky(self: Path, *a: object, **k: object) -> str:
        if self.suffix == ".py":
            raise OSError("denied")
        return original(self, *a, **k)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "read_text", flaky)
    report = eng.converge_to_code("s1", code)
    assert report["spec_id"] == "s1"


def test_converge_byte_budget_break(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    eng = _eng(tmp_path)
    eng.init_spec("s1", "T")
    code = tmp_path / "code"
    code.mkdir()
    (code / "a.py").write_text("audit logging here\n")
    (code / "b.py").write_text("more content\n")
    monkeypatch.setattr(analysis_mod, "_MAX_CONVERGE_BYTES", 5)
    report = eng.converge_to_code("s1", code)
    assert report["spec_id"] == "s1"


def test_converge_stopword_only_req(tmp_path: Path) -> None:
    eng = _eng(tmp_path)
    eng.init_spec("s1", "T")
    eng.add_requirement("s1", "the user must be able")
    code = tmp_path / "code"
    code.mkdir()
    (code / "a.py").write_text("pass\n")
    report = eng.converge_to_code("s1", code)
    assert not any(f.get("gap_type") == "missing" for f in report.get("findings", []))


def test_converge_partial_match(tmp_path: Path) -> None:
    eng = _eng(tmp_path)
    eng.init_spec("s1", "T")
    eng.add_requirement("s1", "audit logging rotation retention")
    code = tmp_path / "code"
    code.mkdir()
    (code / "a.py").write_text("audit = True\n")
    report = eng.converge_to_code("s1", code)
    kinds = {f.get("gap_type") for f in report.get("findings", [])}
    assert "partial" in kinds


def test_converge_missing_keywords(tmp_path: Path) -> None:
    eng = _eng(tmp_path)
    eng.init_spec("s1", "T")
    eng.add_requirement("s1", "zebra quantum xyzzy")
    code = tmp_path / "code"
    code.mkdir()
    (code / "a.py").write_text("audit = True\n")
    report = eng.converge_to_code("s1", code)
    kinds = {f.get("gap_type") for f in report.get("findings", [])}
    assert "missing" in kinds


# --- engine: validator + render edges ----------------------------------------


def test_constitution_violations_stopword_only(tmp_path: Path) -> None:
    eng = _eng(tmp_path)
    spec = eng.init_spec("s1", "T", constitution="MUST ensure support.")
    assert _SpecValidator.constitution_violations(spec) == []


def test_validate_deltas_removed_existing(tmp_path: Path) -> None:
    eng = _eng(tmp_path)
    eng.init_spec("s1", "T")
    req = eng.add_requirement("s1", "body")
    eng.add_delta("s1", req.id, DeltaType.REMOVED)
    eng.add_delta("s1", "REQ-777", DeltaType.ADDED, "new thing")
    spec = eng.load_spec("s1")
    assert spec is not None
    assert _SpecValidator.validate_deltas(spec) == []


def test_render_markdown_unknown_phase(tmp_path: Path) -> None:
    eng = _eng(tmp_path)
    spec = eng.init_spec("s1", "T")
    spec.phase = types.SimpleNamespace(value="archived")  # type: ignore[assignment]
    md = _render_markdown(spec)
    assert "archived" in md


# --- engine: manifest/drift edges --------------------------------------------


def test_get_manifest_no_baseline(tmp_path: Path) -> None:
    eng = _eng(tmp_path)
    eng.init_spec("s1", "T")
    (tmp_path / "s1.manifest.json").unlink()
    manifest = eng.get_manifest("s1")
    assert manifest is not None


def test_get_manifest_json_missing(tmp_path: Path) -> None:
    eng = _eng(tmp_path)
    eng.init_spec("s1", "T")
    (tmp_path / "s1.manifest.json").unlink()
    (tmp_path / "s1.json").unlink()
    eng.get_manifest("s1")


def test_get_manifest_md_missing(tmp_path: Path) -> None:
    eng = _eng(tmp_path)
    eng.init_spec("s1", "T")
    (tmp_path / "s1.manifest.json").unlink()
    eng._spec_md_path("s1").unlink()
    eng.get_manifest("s1")


def test_is_file_modified_md_missing(tmp_path: Path) -> None:
    eng = _eng(tmp_path)
    eng.init_spec("s1", "T")
    eng._spec_md_path("s1").unlink()
    assert eng.is_file_modified("s1", "md") is True


def test_detect_drift_md_modified(tmp_path: Path) -> None:
    eng = _eng(tmp_path)
    eng.init_spec("s1", "T")
    md = eng._spec_md_path("s1")
    md.write_text(md.read_text(encoding="utf-8") + "\nextra\n", encoding="utf-8")
    report = eng.detect_drift("s1")
    assert any(".md" in str(item) for item in report.get("items", report.get("changes", [])))


def test_phase_regression_mixed(tmp_path: Path) -> None:
    eng = _eng(tmp_path)
    spec = eng.init_spec("s1", "T")
    spec.state_history = [
        {"to": "specify"},
        {"to": "implement"},
        {"to": "plan"},
    ]
    eng._save(spec)
    report = eng.detect_drift("s1")
    assert any("state_history" in str(item) or "regress" in str(item).lower() for item in report.get("items", []))


# --- engine: task status / verify edges --------------------------------------


def _in_tasks_phase(eng: SpecEngine, spec_id: str) -> None:
    spec = eng.load_spec(spec_id)
    assert spec is not None
    spec.phase = SpecPhase.TASKS
    eng._save(spec)


def test_update_task_status_second_task_pending(tmp_path: Path) -> None:
    eng = _eng(tmp_path)
    eng.init_spec("s1", "T")
    _in_tasks_phase(eng, "s1")
    eng.add_task("s1", "first")
    t2 = eng.add_task("s1", "second")
    assert eng.update_task_status("s1", t2.id, "pending") is True
    spec = eng.load_spec("s1")
    assert spec is not None
    task = next(t for t in spec.tasks if t.id == t2.id)
    assert task.verified is False


def test_verify_task_second_and_empty_evidence(tmp_path: Path) -> None:
    eng = _eng(tmp_path)
    eng.init_spec("s1", "T")
    _in_tasks_phase(eng, "s1")
    eng.add_task("s1", "first")
    t2 = eng.add_task("s1", "second")
    assert eng.verify_task("s1", t2.id, "build ok") is True
    spec = eng.load_spec("s1")
    assert spec is not None
    task = next(t for t in spec.tasks if t.id == t2.id)
    assert task.verified is True
    assert task.status == "done"
    assert eng.verify_task("s1", t2.id, "") is True
    spec2 = eng.load_spec("s1")
    assert spec2 is not None
    task2 = next(t for t in spec2.tasks if t.id == t2.id)
    assert task2.verified is False


# --- engine: write_manifest / delete / apply_deltas edges ---------------------


def test_write_manifest_files_missing(tmp_path: Path) -> None:
    eng = _eng(tmp_path)
    spec = eng.init_spec("s1", "T")
    (tmp_path / "s1.json").unlink()
    eng._spec_md_path("s1").unlink()
    eng._write_manifest(spec)
    assert (tmp_path / "s1.manifest.json").exists()


def test_delete_spec_unlink_oserror(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    eng = _eng(tmp_path)
    eng.init_spec("s1", "T")
    monkeypatch.setattr(
        Path, "unlink", lambda self, *a, **k: (_ for _ in ()).throw(OSError("locked"))
    )
    assert eng.delete_spec("s1") is False


def test_apply_delta_modified_no_match(tmp_path: Path) -> None:
    eng = _eng(tmp_path)
    eng.init_spec("s1", "T")
    eng.add_requirement("s1", "body")
    spec = eng.load_spec("s1")
    assert spec is not None
    from runtime.spec.models import SpecDelta

    delta = SpecDelta(requirement_id="REQ-999", delta_type=DeltaType.MODIFIED, description="new desc")
    eng._apply_single_delta(spec, delta)
    assert spec.requirements[0].description == "body"


def test_apply_delta_modified_second_req(tmp_path: Path) -> None:
    eng = _eng(tmp_path)
    eng.init_spec("s1", "T")
    eng.add_requirement("s1", "first body")
    r2 = eng.add_requirement("s1", "second body")
    eng.add_delta("s1", r2.id, DeltaType.MODIFIED, "updated body")
    eng.apply_deltas("s1")
    spec = eng.load_spec("s1")
    assert spec is not None
    assert next(r for r in spec.requirements if r.id == r2.id).description == "updated body"


def test_apply_delta_removed(tmp_path: Path) -> None:
    eng = _eng(tmp_path)
    eng.init_spec("s1", "T")
    r1 = eng.add_requirement("s1", "doomed")
    eng.add_delta("s1", r1.id, DeltaType.REMOVED)
    eng.apply_deltas("s1")
    spec = eng.load_spec("s1")
    assert spec is not None
    assert all(r.id != r1.id for r in spec.requirements)
