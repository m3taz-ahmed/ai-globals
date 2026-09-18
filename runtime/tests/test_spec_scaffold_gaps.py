"""Gap coverage: runtime/spec/scaffold.py — ScaffoldingMixin paths."""

from __future__ import annotations

from pathlib import Path

import pytest

from runtime.spec.models import Spec
from runtime.spec.scaffold import ScaffoldingMixin


class _Host(ScaffoldingMixin):
    def __init__(self, specs_dir: Path) -> None:
        self.specs_dir = specs_dir
        self._specs: dict[str, Spec] = {}
        self.saved: list[str] = []

    def load_spec(self, spec_id: str) -> Spec | None:
        return self._specs.get(spec_id)

    def _save(self, spec: Spec) -> None:
        self._specs[spec.id] = spec
        self.saved.append(spec.id)

    def _spec_md_path(self, spec_id: str) -> Path:
        return self.specs_dir / f"{spec_id}.md"


class TestScaffold:
    def test_spec_new_and_existing(self, tmp_path: Path) -> None:
        h = _Host(tmp_path)
        h.scaffold_spec("s1", "Title", "desc")
        assert (tmp_path / "s1.spec.md").exists()
        h._specs["s2"] = Spec(id="s2", title="T2")
        out2 = h.scaffold_spec("s2", "ignored")
        assert isinstance(out2, str)

    def test_plan_tasks_checklist(self, tmp_path: Path) -> None:
        h = _Host(tmp_path)
        assert h.scaffold_plan("ghost") == ""
        assert h.scaffold_tasks("ghost") == ""
        assert h.scaffold_checklist("ghost") == ""
        h._specs["s"] = Spec(id="s", title="T")
        assert h.scaffold_plan("s") != ""
        assert h.scaffold_tasks("s") != ""
        assert h.scaffold_checklist("s") != ""
        assert (tmp_path / "s.plan.md").exists()
        assert (tmp_path / "s.tasks.md").exists()
        assert (tmp_path / "s.checklist.md").exists()

    def test_write_scaffold_empty_content(self, tmp_path: Path) -> None:
        h = _Host(tmp_path)
        h._write_scaffold("x", "spec.md", "")
        assert not (tmp_path / "x.spec.md").exists()

    def test_set_constitution(self, tmp_path: Path) -> None:
        h = _Host(tmp_path)
        with pytest.raises(ValueError, match="not found"):
            h.set_constitution("ghost", "rules")
        h._specs["s"] = Spec(id="s", title="T")
        h.set_constitution("s", "governing rules")
        assert h._specs["s"].constitution == "governing rules"
        assert "s" in h.saved

    def test_validate_checklist_missing_spec(self, tmp_path: Path) -> None:
        h = _Host(tmp_path)
        out = h.validate_checklist("ghost")
        assert "error" in out

    def test_validate_checklist_no_md(self, tmp_path: Path) -> None:
        h = _Host(tmp_path)
        h._specs["s"] = Spec(id="s", title="T")
        out = h.validate_checklist("s")
        assert out["total_checks"] == 7 and out["failed"] > 0
        assert out["failing_items"]

    def test_validate_checklist_with_md(self, tmp_path: Path) -> None:
        h = _Host(tmp_path)
        spec = Spec(id="s", title="T")
        spec.requirements.append(object())  # type: ignore[arg-type]
        h._specs["s"] = spec
        (tmp_path / "s.md").write_text(
            "User Story x\nSuccess Criteria SC-1\nEdge Cases\nAssumptions\n"
        )
        out = h.validate_checklist("s")
        assert out["failed"] == 0 and out["passed"] == out["total_checks"]
