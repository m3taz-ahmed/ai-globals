"""Gap coverage for runtime/semantic_search.py + runtime/astryx.py."""

from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import patch

from runtime.astryx import AstryxLinter, _AstryxVisitor
from runtime.semantic_search import (
    SemanticCodeSearch,
    _build_func_lookup,
    _vector_only_results,
    set_hybrid_backends,
)


class TestSemanticSearchGaps:
    def test_index_file_read_oserror(self, tmp_path: Path) -> None:
        f = tmp_path / "mod.py"
        f.write_text("def alpha_func():\n    return 1\n")
        orig = Path.read_text
        calls = {"n": 0}

        def flaky(self: Path, *a: object, **k: object) -> str:
            calls["n"] += 1
            if calls["n"] >= 2:
                raise OSError("denied")
            return orig(self, *a, **k)  # type: ignore[arg-type]

        s = SemanticCodeSearch()
        with patch.object(Path, "read_text", flaky):
            s.index_file(f)
        assert any(fn.name == "alpha_func" for fn in s._functions)

    def test_score_unknown_func(self) -> None:
        s = SemanticCodeSearch()
        assert s._score(["tok"], "ghost_func", 5) == 0.0

    def test_vector_only_results_lookup_fill(self, tmp_path: Path) -> None:
        f = tmp_path / "m.py"
        f.write_text("def zeta_unique_fn():\n    return 1\n")
        ks = SemanticCodeSearch()
        ks.index_file(f)
        set_hybrid_backends(keyword_search=ks)
        try:
            out = _vector_only_results([("zeta_unique_fn", 0.9), ("ghost_vid", 0.5)], [], 10)
        finally:
            set_hybrid_backends()
        names = [r.function.name for r in out]
        assert "zeta_unique_fn" in names
        assert "ghost_vid" not in names

    def test_build_func_lookup_fill(self, tmp_path: Path) -> None:
        f = tmp_path / "m2.py"
        f.write_text("def eta_unique_fn():\n    return 2\n")
        ks = SemanticCodeSearch()
        ks.index_file(f)
        set_hybrid_backends(keyword_search=ks)
        try:
            lookup = _build_func_lookup([])
        finally:
            set_hybrid_backends()
        assert "eta_unique_fn" in lookup


class TestAstryxGaps:
    def test_broad_except_flagged(self) -> None:
        findings = AstryxLinter().lint_text("try:\n    pass\nexcept Exception:\n    pass\n")
        assert any(f.rule == "no-broad-except" for f in findings)

    def test_bare_except_flagged(self) -> None:
        findings = AstryxLinter().lint_text("try:\n    pass\nexcept:\n    pass\n")
        assert any(f.rule == "no-bare-except" for f in findings)

    def test_function_without_end_lineno(self) -> None:
        node = ast.FunctionDef(
            name="f",
            args=ast.arguments(posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[]),
            body=[ast.Pass()],
            decorator_list=[],
            lineno=1,
        )
        node.end_lineno = None
        v = _AstryxVisitor()
        v._check_function(node)  # no crash; fallback branch

    def test_scalar_default_skipped(self) -> None:
        findings = AstryxLinter().lint_text("def f(x=1, y='a'):\n    return x\n")
        assert not any(f.rule == "no-mutable-default" for f in findings)

    def test_mutable_default_flagged(self) -> None:
        findings = AstryxLinter().lint_text("def f(x=[]):\n    return x\n")
        assert any(f.rule == "no-mutable-default" for f in findings)

    def test_lint_directory_path(self, tmp_path: Path) -> None:
        findings = AstryxLinter().lint(tmp_path)
        assert findings[0].rule == "file-read-error"
