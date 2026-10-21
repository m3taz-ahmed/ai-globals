"""Tests for scripts/validate-globals.py check_runtime_exports.

Regression coverage for the skill_routing purge residue: 70 names in
runtime/__init__.py ``__all__`` with no _LAZY_TABLE entry and no submodule -
``from runtime import PersonaDetectorV2`` raised ImportError while
validate-globals still reported success.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_VALIDATE = Path(__file__).resolve().parent.parent.parent / "scripts" / "validate-globals.py"


def _load_validator():
    spec = importlib.util.spec_from_file_location("validate_globals", _VALIDATE)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def validator():
    return _load_validator()


def _runtime_tree(root: Path, init_body: str, modules: list[str] | None = None) -> Path:
    runtime = root / "runtime"
    runtime.mkdir(parents=True)
    (runtime / "__init__.py").write_text(init_body, encoding="utf-8")
    for name in modules or []:
        (runtime / f"{name}.py").write_text("", encoding="utf-8")
    return root


def _ctx(validator):
    return validator.ValidationContext(
        fix=False, interactive=False, dry_run=True, force=False
    )


_INIT_TEMPLATE = '''_LAZY_TABLE = (
{lazy}
)
__all__ = [
{exports}
]
'''


def _init(lazy: list[tuple[str, str]], exports: list[str]) -> str:
    lazy_src = "\n".join(f'    ("{n}", "runtime.{m}", "{n}"),' for n, m in lazy)
    exports_src = "\n".join(f'    "{e}",' for e in exports)
    return _INIT_TEMPLATE.format(lazy=lazy_src, exports=exports_src)


class TestCheckRuntimeExports:
    def test_passes_when_all_exports_resolve(self, validator, tmp_path: Path):
        root = _runtime_tree(
            tmp_path,
            _init(lazy=[("Evidence", "evidence")], exports=["Evidence", "kernel"]),
            modules=["evidence", "kernel"],
        )
        ctx = _ctx(validator)
        validator.check_runtime_exports(str(root), ctx)
        assert ctx.error_count == 0

    def test_fails_on_dangling_export(self, validator, tmp_path: Path):
        root = _runtime_tree(
            tmp_path,
            _init(lazy=[], exports=["PersonaDetectorV2", "Evidence"]),
            modules=["evidence"],
        )
        ctx = _ctx(validator)
        validator.check_runtime_exports(str(root), ctx)
        assert ctx.error_count == 1

    def test_fails_on_lazy_table_missing_module(self, validator, tmp_path: Path):
        root = _runtime_tree(
            tmp_path,
            _init(lazy=[("SkillRouter", "skill_routing")], exports=["SkillRouter"]),
            modules=[],
        )
        ctx = _ctx(validator)
        validator.check_runtime_exports(str(root), ctx)
        assert ctx.error_count == 1  # missing runtime/skill_routing.py only

    def test_export_resolves_via_submodule_without_lazy_entry(self, validator, tmp_path: Path):
        root = _runtime_tree(
            tmp_path,
            _init(lazy=[], exports=["subpkg"]),
            modules=["subpkg"],
        )
        ctx = _ctx(validator)
        validator.check_runtime_exports(str(root), ctx)
        assert ctx.error_count == 0

    def test_current_runtime_has_no_dangling_exports(self, validator):
        """The real tree must pass — this is the regression guard."""
        root = _VALIDATE.parent.parent
        ctx = _ctx(validator)
        validator.check_runtime_exports(str(root), ctx)
        assert ctx.error_count == 0

    def test_missing_init_is_noop(self, validator, tmp_path: Path):
        ctx = _ctx(validator)
        validator.check_runtime_exports(str(tmp_path), ctx)
        assert ctx.error_count == 0
