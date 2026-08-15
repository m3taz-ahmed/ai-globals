"""Tests for runtime/review_engine.py — AI code review engine."""

from __future__ import annotations

from pathlib import Path

from runtime.review_engine import (
    CodeReviewEngine,
    ReviewConfig,
    ReviewFinding,
    ReviewReport,
    review_code,
)


class TestReviewFinding:
    """Tests for ReviewFinding."""

    def test_passes_threshold_default(self) -> None:
        f = ReviewFinding("bug", "high", 60, "msg")
        assert f.passes_threshold is True

    def test_below_threshold(self) -> None:
        f = ReviewFinding("bug", "high", 30, "msg")
        assert f.passes_threshold is False


class TestReviewReport:
    """Tests for ReviewReport."""

    def test_empty_report_passes(self) -> None:
        r = ReviewReport()
        assert r.passed is True
        assert r.score == 100

    def test_report_with_critical_fails(self) -> None:
        r = ReviewReport(findings=[ReviewFinding("sec", "critical", 90, "d")])
        assert r.passed is False

    def test_report_with_low_passes(self) -> None:
        r = ReviewReport(findings=[ReviewFinding("style", "low", 60, "d")])
        assert r.passed is True

    def test_report_with_below_threshold_passes(self) -> None:
        r = ReviewReport(findings=[ReviewFinding("sec", "critical", 30, "d")])
        assert r.passed is True  # below threshold

    def test_score_decreases_with_findings(self) -> None:
        r = ReviewReport(findings=[ReviewFinding("bug", "high", 80, "d")])
        assert r.score < 100

    def test_filtered_by_config(self) -> None:
        findings = [
            ReviewFinding("bug", "high", 80, "d1"),
            ReviewFinding("style", "low", 30, "d2"),
            ReviewFinding("security", "critical", 90, "d3"),
        ]
        r = ReviewReport(findings=findings)
        config = ReviewConfig(min_confidence=50, enabled_categories={"bug", "security"})
        filtered = r.filtered(config)
        assert len(filtered) == 2
        assert all(f.category in {"bug", "security"} for f in filtered)

    def test_summary_structure(self) -> None:
        r = ReviewReport(
            file_path="test.py",
            findings=[ReviewFinding("bug", "high", 80, "d")],
            lines_reviewed=10,
        )
        s = r.summary()
        assert s["file"] == "test.py"
        assert s["lines_reviewed"] == 10
        assert s["by_severity"]["high"] == 1


class TestCodeReviewEngine:
    """Tests for CodeReviewEngine."""

    def test_review_clean_code(self) -> None:
        engine = CodeReviewEngine()
        code = "x = 1\nprint(x)\n"
        report = engine.review_diff("", code, Path("test.py"))
        assert report.passed is True

    def test_review_syntax_error(self) -> None:
        engine = CodeReviewEngine()
        code = "def foo(:\n    pass\n"
        report = engine.review_diff("", code, Path("test.py"))
        assert any(f.category == "quality" and f.severity == "critical" for f in report.findings)

    def test_review_bare_except(self) -> None:
        engine = CodeReviewEngine()
        code = "try:\n    x = 1\nexcept:\n    pass\n"
        report = engine.review_diff("", code, Path("test.py"))
        assert any(f.rule_id == "PY-BARE-EXCEPT" for f in report.findings)

    def test_review_mutable_default(self) -> None:
        engine = CodeReviewEngine()
        code = "def foo(x=[]):\n    return x\n"
        report = engine.review_diff("", code, Path("test.py"))
        assert any(f.rule_id == "PY-MUTABLE-DEFAULT" for f in report.findings)

    def test_review_long_function(self) -> None:
        engine = CodeReviewEngine()
        code = "def foo():\n" + "    x = 1\n" * 60 + "\n"
        report = engine.review_diff("", code, Path("test.py"))
        assert any(f.rule_id == "PY-LONG-FUNCTION" for f in report.findings)

    def test_review_todo_no_ticket(self) -> None:
        engine = CodeReviewEngine()
        code = "# TODO: fix this later\nx = 1\n"
        report = engine.review_diff("", code, Path("test.py"))
        assert any(f.rule_id == "PY-TODO-NOTICKET" for f in report.findings)

    def test_review_todo_with_ticket(self) -> None:
        engine = CodeReviewEngine()
        code = "# TODO(JIRA-123): fix this\nx = 1\n"
        report = engine.review_diff("", code, Path("test.py"))
        assert not any(f.rule_id == "PY-TODO-NOTICKET" for f in report.findings)

    def test_review_none_compare(self) -> None:
        engine = CodeReviewEngine()
        code = "if x == None:\n    pass\n"
        report = engine.review_diff("", code, Path("test.py"))
        assert any(f.rule_id == "BUG-NONE-COMPARE" for f in report.findings)

    def test_review_bool_compare(self) -> None:
        engine = CodeReviewEngine()
        code = "if x == True:\n    pass\n"
        report = engine.review_diff("", code, Path("test.py"))
        assert any(f.rule_id == "STYLE-BOOL-COMPARE" for f in report.findings)

    def test_review_silent_except(self) -> None:
        engine = CodeReviewEngine()
        code = "try:\n    x = 1\nexcept Exception:\n    pass\n"
        report = engine.review_diff("", code, Path("test.py"))
        assert any(f.rule_id == "BUG-SILENT-EXCEPT" for f in report.findings)

    def test_review_trailing_whitespace(self) -> None:
        engine = CodeReviewEngine()
        code = "x = 1   \n"
        report = engine.review_diff("", code, Path("test.py"))
        assert any(f.rule_id == "STYLE-TRAILING-WS" for f in report.findings)

    def test_review_long_line(self) -> None:
        engine = CodeReviewEngine()
        code = "x = '" + "a" * 130 + "'\n"
        report = engine.review_diff("", code, Path("test.py"))
        assert any(f.rule_id == "STYLE-LONG-LINE" for f in report.findings)

    def test_review_security_eval(self) -> None:
        engine = CodeReviewEngine()
        code = "eval(user_input)\n"
        report = engine.review_diff("", code, Path("test.py"))
        assert any(f.category == "security" for f in report.findings)

    def test_review_security_secret(self) -> None:
        engine = CodeReviewEngine()
        code = 'api_key = "sk-abc123def456ghi789jkl012mno345pqr678"\n'
        report = engine.review_diff("", code, Path("test.py"))
        assert any(f.category == "security" and f.severity == "critical" for f in report.findings)

    def test_review_console_log(self) -> None:
        engine = CodeReviewEngine()
        code = "console.log('hello')\n"
        report = engine.review_diff("", code, Path("test.js"))
        assert any(f.rule_id == "GEN-CONSOLE-LOG" for f in report.findings)

    def test_review_file(self, tmp_path: Path) -> None:
        f = tmp_path / "test.py"
        f.write_text("eval(x)\n", encoding="utf-8")
        engine = CodeReviewEngine()
        report = engine.review_file(f)
        assert report.file_path == str(f)
        assert len(report.findings) > 0

    def test_review_file_nonexistent(self, tmp_path: Path) -> None:
        engine = CodeReviewEngine()
        report = engine.review_file(tmp_path / "nonexistent.py")
        assert report.findings == []

    def test_review_directory(self, tmp_path: Path) -> None:
        (tmp_path / "safe.py").write_text("x = 1\n", encoding="utf-8")
        (tmp_path / "unsafe.py").write_text("eval(x)\n", encoding="utf-8")
        engine = CodeReviewEngine()
        reports = engine.review_directory(tmp_path)
        assert len(reports) == 2
        total_findings = sum(len(r.findings) for r in reports)
        assert total_findings > 0

    def test_review_with_config_min_confidence(self) -> None:
        config = ReviewConfig(min_confidence=90)
        engine = CodeReviewEngine(config)
        code = "if x == None:\n    pass\n"
        report = engine.review_diff("", code, Path("test.py"))
        filtered = report.filtered(config)
        # None compare has confidence 75, below 90
        assert not any(f.rule_id == "BUG-NONE-COMPARE" for f in filtered)

    def test_review_with_config_categories(self) -> None:
        config = ReviewConfig(enabled_categories={"security"})
        engine = CodeReviewEngine(config)
        code = "if x == None:\n    pass\n"
        report = engine.review_diff("", code, Path("test.py"))
        filtered = report.filtered(config)
        assert all(f.category == "security" for f in filtered)

    def test_review_code_convenience(self, tmp_path: Path) -> None:
        f = tmp_path / "test.py"
        f.write_text("eval(x)\n", encoding="utf-8")
        report = review_code(f)
        assert len(report.findings) > 0

    def test_review_diff_lines_reviewed(self) -> None:
        engine = CodeReviewEngine()
        code = "x = 1\ny = 2\nz = 3\n"
        report = engine.review_diff("", code, Path("test.py"))
        # split("\n") on trailing newline produces an extra empty string
        assert report.lines_reviewed >= 3


class TestEdgeCases:
    """Tests for edge cases and error paths."""

    def test_review_directory_skips_non_file(self, tmp_path: Path) -> None:
        """Line 190: non-file entries (directories) are skipped in review_directory."""
        (tmp_path / "safe.py").write_text("x = 1\n", encoding="utf-8")
        (tmp_path / "subdir").mkdir()  # directory entry — should be skipped
        engine = CodeReviewEngine()
        reports = engine.review_directory(tmp_path)
        assert len(reports) == 1  # only safe.py, not subdir

    def test_review_directory_skips_unsupported_extension(self, tmp_path: Path) -> None:
        """Line 192: files with unsupported extensions are skipped."""
        (tmp_path / "safe.py").write_text("x = 1\n", encoding="utf-8")
        (tmp_path / "data.xml").write_text("eval(x)\n", encoding="utf-8")
        engine = CodeReviewEngine()
        reports = engine.review_directory(tmp_path)
        assert len(reports) == 1  # only .py, .xml skipped

    def test_review_directory_skips_excluded_dirs(self, tmp_path: Path) -> None:
        """Line 194: files in excluded directories (.git, __pycache__, etc.) are skipped."""
        (tmp_path / "safe.py").write_text("x = 1\n", encoding="utf-8")
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "config.py").write_text("eval(x)\n", encoding="utf-8")
        engine = CodeReviewEngine()
        reports = engine.review_directory(tmp_path)
        assert len(reports) == 1  # only safe.py, .git/config.py skipped

    def test_review_performance_string_concat_in_loop(self) -> None:
        """Line 386: string concatenation in loop triggers PERF-STR-CONCAT."""
        engine = CodeReviewEngine()
        # Line exactly "for " followed by a line with + 'string'
        code = "for \nresult = result + 'hello'\n"
        report = engine.review_diff("", code, Path("test.py"))
        assert any(f.rule_id == "PERF-STR-CONCAT" for f in report.findings)

    def test_review_performance_list_append_in_loop(self) -> None:
        """Line 397: list.append in for-loop triggers PERF-LIST-APPEND."""
        engine = CodeReviewEngine()
        code = "for item in items:\n    result.append(item)\n"
        report = engine.review_diff("", code, Path("test.py"))
        assert any(f.rule_id == "PERF-LIST-APPEND" for f in report.findings)

    def test_main_block_with_file(self, tmp_path: Path) -> None:
        """Lines 416-430: __main__ block with a file argument (else branch)."""
        import runpy
        import sys

        f = tmp_path / "test.py"
        f.write_text("eval(x)\n", encoding="utf-8")
        script = str(Path(__file__).resolve().parent.parent / "review_engine.py")
        old_argv = sys.argv
        sys.argv = [script, str(f)]
        try:
            runpy.run_path(script, run_name="__main__")
        finally:
            sys.argv = old_argv

    def test_main_block_with_directory(self, tmp_path: Path) -> None:
        """Lines 416-430: __main__ block with a directory argument (is_dir branch)."""
        import runpy
        import sys

        (tmp_path / "safe.py").write_text("x = 1\n", encoding="utf-8")
        script = str(Path(__file__).resolve().parent.parent / "review_engine.py")
        old_argv = sys.argv
        sys.argv = [script, str(tmp_path)]
        try:
            runpy.run_path(script, run_name="__main__")
        finally:
            sys.argv = old_argv
