"""Gap coverage: runtime/plan_diff_validator.py."""

from __future__ import annotations

import json
from pathlib import Path

from runtime.plan_diff_validator import (
    Finding,
    PlanDiffValidator,
    ValidationLevel,
    ValidationResult,
)


class TestResultHelpers:
    def test_finding_and_result_dicts(self) -> None:
        f = Finding(ValidationLevel.ERROR, "rule1", "msg", file="f.py")
        assert f.to_dict()["level"] == "error"
        r = ValidationResult()
        assert r.ok
        r.findings.append(Finding(ValidationLevel.WARN, "w", "m"))
        assert r.ok and r.warnings
        r.findings.append(f)
        assert not r.ok and r.errors == [f]
        d = r.to_dict()
        assert "findings" in d


class TestPlanExtraction:
    def test_code_blocks_and_bullets(self, tmp_path: Path) -> None:
        v = PlanDiffValidator(tmp_path)
        plan = """# Plan
- src/app.py
- not-a-path
```
docs/readme.md
# comment.py
// comment.ts
plain text
```
"""
        files = v.extract_plan_files(plan)
        assert "src/app.py" in files and "docs/readme.md" in files
        assert "# comment.py" not in files and "not-a-path" not in files

    def test_dedup(self, tmp_path: Path) -> None:
        v = PlanDiffValidator(tmp_path)
        files = v.extract_plan_files("- a/b.py\n- a/b.py\n")
        assert files == ["a/b.py"]

    def test_validate_plan_paths(self, tmp_path: Path) -> None:
        v = PlanDiffValidator(tmp_path, max_files=1)
        res = v.validate_plan("- src/.env\n- a/b.py\n- c/d.py\n")
        codes = {f.rule for f in res.findings}
        assert "forbidden_path" in codes and "file_count" in codes
        assert not res.ok

    def test_validate_plan_empty_warn(self, tmp_path: Path) -> None:
        v = PlanDiffValidator(tmp_path)
        res = v.validate_plan("# Plan\nno files here\n")
        assert any(f.rule == "empty_plan" for f in res.findings)


class TestDiffValidation:
    def _diff(self, *files: str) -> str:
        return "".join(f"--- a/{f}\n+++ b/{f}\n@@ -1 +2 @@\n" for f in files)

    def test_extract_and_forbidden(self, tmp_path: Path) -> None:
        v = PlanDiffValidator(tmp_path)
        diff = self._diff("src/x.py", "secrets/key.pem")
        assert "src/x.py" in v.extract_diff_files(diff)
        res = v.validate_diff(diff)
        assert any(f.rule == "forbidden_path" for f in res.findings)

    def test_test_gap(self, tmp_path: Path) -> None:
        v = PlanDiffValidator(tmp_path)
        res = v.validate_diff(self._diff("src/x.py"))
        assert any(f.rule == "test_gap" for f in res.findings)
        res2 = v.validate_diff(self._diff("src/x.py", "tests/test_x.py"))
        assert not any(f.rule == "test_gap" for f in res2.findings)

    def test_undeclared_imports(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(json.dumps({"dependencies": {"react": "^1"}}))
        (tmp_path / "requirements.txt").write_text("requests>=2\n# comment\n")
        v = PlanDiffValidator(tmp_path)
        diff = (
            "+++ b/src/x.py\n+import os\n+import undeclared_lib\n"
            "+++ b/src/y.ts\n+import x from 'undeclared-pkg'\n"
            "+import y from './rel'\n+import z from '@/alias'\n"
        )
        res = v.validate_diff(diff)
        msgs = [f.message for f in res.findings if f.rule == "undeclared_import"]
        assert any("undeclared_lib" in m for m in msgs)
        assert any("undeclared-pkg" in m for m in msgs)
        assert not any("os" in m or "'./rel'" in m for m in msgs)

    def test_unrelated_refactor(self, tmp_path: Path) -> None:
        v = PlanDiffValidator(tmp_path)
        res = v.validate_diff(self._diff("a/x.py", "b/y.py", "c/z.py"))
        assert any(f.rule == "unrelated_refactor" for f in res.findings)
        res2 = v.validate_diff(self._diff("a/x.py", "a/y.py"))
        assert not any(f.rule == "unrelated_refactor" for f in res2.findings)

    def test_matches_forbidden_variants(self, tmp_path: Path) -> None:
        v = PlanDiffValidator(tmp_path)
        assert v._matches_forbidden(".env") == ".env"
        assert v._matches_forbidden("config/.env.prod") is not None
        assert v._matches_forbidden("src/app.py") is None

    def test_is_test_source_helpers(self) -> None:
        assert PlanDiffValidator._is_test_file("tests/test_x.py")
        assert PlanDiffValidator._is_test_file("a.spec.ts")
        assert not PlanDiffValidator._is_test_file("src/x.py")
        assert PlanDiffValidator._is_source_file("x.go")
        assert not PlanDiffValidator._is_source_file("x.md")

