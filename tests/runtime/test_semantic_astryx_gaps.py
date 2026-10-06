"""Gap coverage for runtime/semantic_search.py + runtime/astryx.py."""

from __future__ import annotations

import ast
from pathlib import Path

from runtime.astryx import AstryxLinter, _AstryxVisitor


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
