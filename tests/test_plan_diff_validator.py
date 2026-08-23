"""Tests for runtime/plan_diff_validator.py — plan and diff validation.

FAST tier — no MCP, no kernel, no model loading.
"""

from __future__ import annotations

import json
from pathlib import Path

from runtime.plan_diff_validator import (
    Finding,
    PlanDiffValidator,
    ValidationLevel,
    ValidationResult,
)


# -- ValidationLevel enum ----------------------------------------------------


class TestValidationLevel:
    def test_error_value(self) -> None:
        assert ValidationLevel.ERROR.value == "error"

    def test_warn_value(self) -> None:
        assert ValidationLevel.WARN.value == "warn"

    def test_info_value(self) -> None:
        assert ValidationLevel.INFO.value == "info"

    def test_is_str_enum(self) -> None:
        assert isinstance(ValidationLevel.ERROR, str)


# -- Finding -----------------------------------------------------------------


class TestFinding:
    def test_to_dict_basic(self) -> None:
        # Arrange
        f = Finding(level=ValidationLevel.ERROR, rule="forbidden_path", message="bad")
        # Act
        d = f.to_dict()
        # Assert
        assert d["level"] == "error"
        assert d["rule"] == "forbidden_path"
        assert d["message"] == "bad"
        assert "file" not in d
        assert "line" not in d

    def test_to_dict_with_file_and_line(self) -> None:
        # Arrange
        f = Finding(
            level=ValidationLevel.WARN, rule="test_gap",
            message="no tests", file="src/app.py", line=10,
        )
        # Act
        d = f.to_dict()
        # Assert
        assert d["file"] == "src/app.py"
        assert d["line"] == 10


# -- ValidationResult --------------------------------------------------------


class TestValidationResult:
    def test_ok_with_no_findings(self) -> None:
        # Arrange
        result = ValidationResult()
        # Act + Assert
        assert result.ok is True
        assert result.errors == []
        assert result.warnings == []

    def test_ok_false_with_error_finding(self) -> None:
        # Arrange
        result = ValidationResult()
        result.findings.append(
            Finding(ValidationLevel.ERROR, "forbidden_path", "bad")
        )
        # Act + Assert
        assert result.ok is False
        assert len(result.errors) == 1

    def test_warnings_filtered(self) -> None:
        # Arrange
        result = ValidationResult()
        result.findings.append(Finding(ValidationLevel.WARN, "test_gap", "w"))
        result.findings.append(Finding(ValidationLevel.ERROR, "bad", "e"))
        # Act + Assert
        assert len(result.warnings) == 1
        assert len(result.errors) == 1

    def test_to_dict(self) -> None:
        # Arrange
        result = ValidationResult()
        result.findings.append(Finding(ValidationLevel.ERROR, "r1", "m1"))
        result.plan_files = ["src/a.py"]
        # Act
        d = result.to_dict()
        # Assert
        assert d["ok"] is False
        assert d["error_count"] == 1
        assert d["warn_count"] == 0
        assert d["plan_files"] == ["src/a.py"]
        assert len(d["findings"]) == 1


# -- extract_plan_files ------------------------------------------------------


class TestExtractPlanFiles:
    def test_extract_from_code_block(self, tmp_path: Path) -> None:
        # Arrange
        plan = "```\nsrc/main.py\nsrc/utils.py\n```"
        v = PlanDiffValidator(tmp_path)
        # Act
        files = v.extract_plan_files(plan)
        # Assert
        assert "src/main.py" in files
        assert "src/utils.py" in files

    def test_extract_from_bullet_list(self, tmp_path: Path) -> None:
        # Arrange
        plan = "- src/main.py\n- tests/test_main.py"
        v = PlanDiffValidator(tmp_path)
        # Act
        files = v.extract_plan_files(plan)
        # Assert
        assert "src/main.py" in files
        assert "tests/test_main.py" in files

    def test_dedup_preserving_order(self, tmp_path: Path) -> None:
        # Arrange
        plan = "```\nsrc/a.py\nsrc/b.py\nsrc/a.py\n```"
        v = PlanDiffValidator(tmp_path)
        # Act
        files = v.extract_plan_files(plan)
        # Assert
        assert files == ["src/a.py", "src/b.py"]


# -- validate_plan -----------------------------------------------------------


class TestValidatePlan:
    def test_forbidden_path_produces_error(self, tmp_path: Path) -> None:
        # Arrange — secrets/ is a forbidden pattern; path has "/" so it's extracted
        plan = "```\nsecrets/api_keys.py\nsrc/main.py\n```"
        v = PlanDiffValidator(tmp_path)
        # Act
        result = v.validate_plan(plan)
        # Assert
        assert result.ok is False
        assert any(f.rule == "forbidden_path" for f in result.errors)

    def test_file_count_warn_when_exceeds_max(self, tmp_path: Path) -> None:
        # Arrange
        files = [f"src/file_{i}.py" for i in range(25)]
        plan = "```\n" + "\n".join(files) + "\n```"
        v = PlanDiffValidator(tmp_path, max_files=20)
        # Act
        result = v.validate_plan(plan)
        # Assert
        assert result.ok is True
        assert any(f.rule == "file_count" for f in result.warnings)

    def test_empty_plan_warns_when_header_present(self, tmp_path: Path) -> None:
        # Arrange
        plan = "# Plan\n\nNo files mentioned here."
        v = PlanDiffValidator(tmp_path)
        # Act
        result = v.validate_plan(plan)
        # Assert
        assert any(f.rule == "empty_plan" for f in result.warnings)

    def test_clean_plan_passes(self, tmp_path: Path) -> None:
        # Arrange
        plan = "```\nsrc/main.py\n```"
        v = PlanDiffValidator(tmp_path)
        # Act
        result = v.validate_plan(plan)
        # Assert
        assert result.ok is True
        assert result.warnings == []


# -- extract_diff_files ------------------------------------------------------


class TestExtractDiffFiles:
    def test_extract_from_unified_diff(self, tmp_path: Path) -> None:
        # Arrange
        diff = (
            "diff --git a/src/a.py b/src/a.py\n"
            "+++ b/src/a.py\n"
            "@@ -1,3 +1,4 @@\n"
            "+new line\n"
        )
        v = PlanDiffValidator(tmp_path)
        # Act
        files = v.extract_diff_files(diff)
        # Assert
        assert files == ["src/a.py"]

    def test_extract_multiple_files(self, tmp_path: Path) -> None:
        # Arrange
        diff = "+++ b/src/a.py\n+++ b/src/b.py\n"
        v = PlanDiffValidator(tmp_path)
        # Act
        files = v.extract_diff_files(diff)
        # Assert
        assert files == ["src/a.py", "src/b.py"]


# -- validate_diff -----------------------------------------------------------


class TestValidateDiff:
    def test_forbidden_path_error(self, tmp_path: Path) -> None:
        # Arrange
        diff = "+++ b/.env\n"
        v = PlanDiffValidator(tmp_path)
        # Act
        result = v.validate_diff(diff)
        # Assert
        assert result.ok is False
        assert any(f.rule == "forbidden_path" for f in result.errors)

    def test_test_gap_warn_when_no_tests(self, tmp_path: Path) -> None:
        # Arrange
        diff = "+++ b/src/a.py\n+++ b/src/b.py\n"
        v = PlanDiffValidator(tmp_path)
        # Act
        result = v.validate_diff(diff)
        # Assert
        assert any(f.rule == "test_gap" for f in result.warnings)

    def test_file_count_warn_when_exceeds_max(self, tmp_path: Path) -> None:
        # Arrange
        lines = [f"+++ b/src/file_{i}.py" for i in range(25)]
        diff = "\n".join(lines) + "\n"
        v = PlanDiffValidator(tmp_path, max_files=20)
        # Act
        result = v.validate_diff(diff)
        # Assert
        assert any(f.rule == "file_count" for f in result.warnings)

    def test_clean_diff_with_tests_passes(self, tmp_path: Path) -> None:
        # Arrange
        diff = "+++ b/src/a.py\n+++ b/tests/test_a.py\n"
        v = PlanDiffValidator(tmp_path)
        # Act
        result = v.validate_diff(diff)
        # Assert
        assert result.ok is True


# -- _check_undeclared_imports -----------------------------------------------


class TestCheckUndeclaredImports:
    def test_warn_on_undeclared_python_import(self, tmp_path: Path) -> None:
        # Arrange
        (tmp_path / "pyproject.toml").write_text(
            "[project]\ndependencies = [\n  \"requests>=2.0\",\n]\n",
            encoding="utf-8",
        )
        (tmp_path / "package.json").write_text(
            json.dumps({"dependencies": {"lodash": "^4.0"}}), encoding="utf-8"
        )
        diff = "+++ b/src/a.py\n+import numpy\n"
        v = PlanDiffValidator(tmp_path)
        # Act
        result = v.validate_diff(diff)
        # Assert
        assert any(
            f.rule == "undeclared_import" and "numpy" in f.message
            for f in result.warnings
        )

    def test_warn_on_undeclared_ts_import(self, tmp_path: Path) -> None:
        # Arrange
        (tmp_path / "package.json").write_text(
            json.dumps({"dependencies": {"react": "^18.0"}}), encoding="utf-8"
        )
        diff = "+++ b/src/a.ts\n+import axios from 'axios'\n"
        v = PlanDiffValidator(tmp_path)
        # Act
        result = v.validate_diff(diff)
        # Assert
        assert any(
            f.rule == "undeclared_import" and "axios" in f.message
            for f in result.warnings
        )

    def test_no_warn_for_declared_dependency(self, tmp_path: Path) -> None:
        # Arrange — requirements.txt format is parsed line-by-line
        (tmp_path / "requirements.txt").write_text(
            "requests>=2.0\n", encoding="utf-8"
        )
        diff = "+++ b/src/a.py\n+import requests\n"
        v = PlanDiffValidator(tmp_path)
        # Act
        result = v.validate_diff(diff)
        # Assert
        assert not any(
            f.rule == "undeclared_import" and "requests" in f.message
            for f in result.warnings
        )

    def test_no_warn_for_stdlib_import(self, tmp_path: Path) -> None:
        # Arrange
        (tmp_path / "pyproject.toml").write_text(
            "[project]\ndependencies = []\n", encoding="utf-8"
        )
        diff = "+++ b/src/a.py\n+import os\n"
        v = PlanDiffValidator(tmp_path)
        # Act
        result = v.validate_diff(diff)
        # Assert
        assert not any(f.rule == "undeclared_import" for f in result.warnings)


# -- _connected_components ---------------------------------------------------


class TestConnectedComponents:
    def test_group_by_top_level_dir(self, tmp_path: Path) -> None:
        # Arrange
        files = ["src/a.py", "src/b.py", "tests/t.py"]
        v = PlanDiffValidator(tmp_path)
        # Act
        components = v._connected_components(files)
        # Assert
        assert len(components) == 2
        src_group = [c for c in components if "src/a.py" in c]
        assert len(src_group) == 1
        assert set(src_group[0]) == {"src/a.py", "src/b.py"}

    def test_single_file_grouped_as_root(self, tmp_path: Path) -> None:
        # Arrange
        files = ["standalone.py"]
        v = PlanDiffValidator(tmp_path)
        # Act
        components = v._connected_components(files)
        # Assert
        assert len(components) == 1
        assert components[0] == ["standalone.py"]


# -- _check_unrelated_refactor -----------------------------------------------


class TestCheckUnrelatedRefactor:
    def test_warn_when_multiple_components(self, tmp_path: Path) -> None:
        # Arrange — 3+ files across 2 top-level dirs
        diff = (
            "+++ b/src/a.py\n"
            "+++ b/src/b.py\n"
            "+++ b/docs/readme.md\n"
        )
        v = PlanDiffValidator(tmp_path)
        # Act
        result = v.validate_diff(diff)
        # Assert
        assert any(f.rule == "unrelated_refactor" for f in result.warnings)

    def test_no_warn_when_single_component(self, tmp_path: Path) -> None:
        # Arrange — all files under same top-level dir
        diff = "+++ b/src/a.py\n+++ b/src/b.py\n+++ b/src/c.py\n"
        v = PlanDiffValidator(tmp_path)
        # Act
        result = v.validate_diff(diff)
        # Assert
        assert not any(f.rule == "unrelated_refactor" for f in result.warnings)

    def test_no_warn_when_fewer_than_three_files(self, tmp_path: Path) -> None:
        # Arrange
        diff = "+++ b/src/a.py\n+++ b/docs/b.md\n"
        v = PlanDiffValidator(tmp_path)
        # Act
        result = v.validate_diff(diff)
        # Assert
        assert not any(f.rule == "unrelated_refactor" for f in result.warnings)
