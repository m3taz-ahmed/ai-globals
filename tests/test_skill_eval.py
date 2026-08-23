"""Tests for runtime/skill_eval.py — self-checking EVAL.md loader.

FAST tier — no MCP, no kernel, no model loading.
"""

from __future__ import annotations

from pathlib import Path

from runtime.skill_eval import (
    CheckStatus,
    EvalCheck,
    SkillEvalResult,
    eval_skill_output,
    has_eval,
    load_eval_file,
    parse_eval_md,
    run_eval,
)


class TestParseEvalMd:
    def test_parse_basic(self) -> None:
        content = """# My skill eval

## Category 1

1. Does the output have a title?
2. Is the output clear?

## Category 2

1. Are there any errors?
"""
        checks = parse_eval_md(content)
        assert len(checks) == 3
        assert checks[0].category == "Category 1"
        assert checks[0].index == 1
        assert "title" in checks[0].text
        assert checks[1].category == "Category 1"
        assert checks[1].index == 2
        assert checks[2].category == "Category 2"

    def test_parse_empty(self) -> None:
        checks = parse_eval_md("")
        assert checks == []

    def test_parse_no_headings(self) -> None:
        checks = parse_eval_md("1. Some check")
        assert checks == []  # No category heading → items ignored


class TestLoadEvalFile:
    def test_load_existing(self, tmp_path: Path) -> None:
        eval_path = tmp_path / "EVAL.md"
        eval_path.write_text("# Test\n\n## Checks\n\n1. Is it good?\n", encoding="utf-8")
        checks = load_eval_file(tmp_path)
        assert checks is not None
        assert len(checks) == 1

    def test_load_missing_returns_none(self, tmp_path: Path) -> None:
        assert load_eval_file(tmp_path) is None


class TestRunEval:
    def test_all_pass(self) -> None:
        checks = [EvalCheck(category="Test", index=1, text="Is it good?")]
        result = run_eval("test-skill", checks, "good output", lambda c, o: "pass")
        assert result.all_passed is True
        assert result.passed == 1
        assert result.failed == 0

    def test_mixed_results(self) -> None:
        checks = [
            EvalCheck(category="A", index=1, text="check 1"),
            EvalCheck(category="A", index=2, text="check 2"),
            EvalCheck(category="B", index=1, text="check 3"),
        ]
        def evaluator(check: str, output: str) -> str:
            if "1" in check:
                return "pass"
            if "2" in check:
                return "fail"
            return "skip"
        result = run_eval("test", checks, "output", evaluator)
        assert result.passed == 1
        assert result.failed == 1
        assert result.skipped == 1
        assert result.all_passed is False

    def test_evaluator_exception(self) -> None:
        checks = [EvalCheck(category="A", index=1, text="check")]
        def bad_evaluator(check: str, output: str) -> str:
            raise RuntimeError("boom")
        result = run_eval("test", checks, "output", bad_evaluator)
        assert result.errors == 1
        assert result.all_passed is False


class TestSkillEvalResult:
    def test_pass_rate(self) -> None:
        result = SkillEvalResult(skill_name="test")
        from runtime.skill_eval import CheckResult
        result.checks = [
            CheckResult(EvalCheck("A", 1, "c1"), CheckStatus.PASS),
            CheckResult(EvalCheck("A", 2, "c2"), CheckStatus.PASS),
            CheckResult(EvalCheck("A", 3, "c3"), CheckStatus.FAIL),
            CheckResult(EvalCheck("A", 4, "c4"), CheckStatus.SKIP),
        ]
        assert result.pass_rate == 2 / 3
        assert result.all_passed is False


class TestHasEval:
    def test_has_eval_true(self, tmp_path: Path) -> None:
        (tmp_path / "EVAL.md").write_text("# Test", encoding="utf-8")
        assert has_eval(tmp_path) is True

    def test_has_eval_false(self, tmp_path: Path) -> None:
        assert has_eval(tmp_path) is False


class TestEvalSkillOutput:
    def test_no_eval_returns_none(self, tmp_path: Path) -> None:
        result = eval_skill_output(tmp_path, "output", lambda c, o: "pass")
        assert result is None

    def test_with_eval(self, tmp_path: Path) -> None:
        (tmp_path / "EVAL.md").write_text(
            "# Test\n\n## Checks\n\n1. Is it good?\n", encoding="utf-8",
        )
        result = eval_skill_output(tmp_path, "good", lambda c, o: "pass")
        assert result is not None
        assert result.skill_name == tmp_path.name
        assert result.all_passed is True
