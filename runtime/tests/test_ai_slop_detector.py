"""Tests for runtime/ai_slop_detector.py — AI slop detection."""

from __future__ import annotations

from pathlib import Path

from runtime.ai_slop_detector import (
    AISlopDetector,
    SlopFinding,
    SlopReport,
    detect_slop,
)


class TestSlopReport:
    """Tests for SlopReport."""

    def test_empty_report_score_100(self) -> None:
        r = SlopReport()
        assert r.score == 100
        assert r.is_clean is True

    def test_score_with_findings(self) -> None:
        r = SlopReport(findings=[SlopFinding("test", "high", "m")])
        assert r.score < 100

    def test_score_minimum_0(self) -> None:
        findings = [SlopFinding("test", "critical", "m") for _ in range(10)]
        r = SlopReport(findings=findings)
        assert r.score == 0

    def test_is_clean_threshold(self) -> None:
        r = SlopReport(findings=[SlopFinding("test", "low", "m")])
        assert r.is_clean is True  # score = 97

    def test_not_clean_with_critical(self) -> None:
        # Two critical findings = score 60, below 80 threshold
        r = SlopReport(findings=[SlopFinding("test", "critical", "m"), SlopFinding("test2", "critical", "m2")])
        assert r.is_clean is False

    def test_summary_structure(self) -> None:
        r = SlopReport(findings=[SlopFinding("cat1", "high", "m1"), SlopFinding("cat2", "low", "m2")])
        s = r.summary()
        assert s["total_findings"] == 2
        assert s["by_category"]["cat1"] == 1
        assert s["by_severity"]["high"] == 1


class TestAISlopDetector:
    """Tests for AISlopDetector."""

    def test_detect_clean_code(self) -> None:
        d = AISlopDetector()
        code = "x = 1\nprint(x)\n"
        report = d.detect(code, Path("test.py"))
        assert report.score == 100

    def test_detect_silent_error_swallowing(self) -> None:
        d = AISlopDetector()
        code = "try:\n    x = 1\nexcept:\n    pass\n"
        report = d.detect(code, Path("test.py"))
        assert any(f.category == "silent_error_swallowing" for f in report.findings)

    def test_detect_empty_stub(self) -> None:
        d = AISlopDetector()
        code = "def foo():\n    pass\n"
        report = d.detect(code, Path("test.py"))
        assert any(f.category == "empty_stub" for f in report.findings)

    def test_detect_redundant_conversion(self) -> None:
        d = AISlopDetector()
        code = "x = str(str(123))\n"
        report = d.detect(code, Path("test.py"))
        assert any(f.category == "redundant_conversion" for f in report.findings)

    def test_detect_dead_branch_return(self) -> None:
        d = AISlopDetector()
        code = "def foo():\n    return 1\n    x = 2\n"
        report = d.detect(code, Path("test.py"))
        assert any(f.category == "dead_branch" for f in report.findings)

    def test_detect_if_false_dead_code(self) -> None:
        d = AISlopDetector()
        code = "if False:\n    print('never')\n"
        report = d.detect(code, Path("test.py"))
        assert any(f.category == "dead_branch" for f in report.findings)

    def test_detect_if_true_placeholder(self) -> None:
        d = AISlopDetector()
        code = "if True:\n    print('always')\n"
        report = d.detect(code, Path("test.py"))
        assert any(f.category == "dead_branch" for f in report.findings)

    def test_detect_copy_paste_repeated(self) -> None:
        d = AISlopDetector()
        code = "print('hello world this is long')\n" * 5
        report = d.detect(code, Path("test.py"))
        assert any(f.category == "copy_paste_leak" for f in report.findings)

    def test_detect_verbose_comment(self) -> None:
        d = AISlopDetector()
        long_comment = "# " + "a" * 110 + "\n"
        report = d.detect(long_comment, Path("test.py"))
        assert any(f.category == "verbose_comment" for f in report.findings)

    def test_detect_overly_broad_try(self) -> None:
        d = AISlopDetector()
        code = "try:\n" + "    x = 1\n" * 55 + "except Exception:\n    pass\n"
        report = d.detect(code, Path("test.py"))
        assert any(f.category == "overly_broad_try" for f in report.findings)

    def test_detect_file(self, tmp_path: Path) -> None:
        f = tmp_path / "test.py"
        f.write_text("try:\n    x = 1\nexcept:\n    pass\n", encoding="utf-8")
        d = AISlopDetector()
        report = d.detect_file(f)
        assert len(report.findings) > 0

    def test_detect_file_nonexistent(self, tmp_path: Path) -> None:
        d = AISlopDetector()
        report = d.detect_file(tmp_path / "nonexistent.py")
        assert report.findings == []

    def test_detect_generic_empty_catch(self) -> None:
        d = AISlopDetector()
        code = "try { something() } catch (e) {}\n"
        report = d.detect(code, Path("test.js"))
        assert any(f.category == "silent_error_swallowing" for f in report.findings)

    def test_detect_no_false_positives_clean(self) -> None:
        d = AISlopDetector()
        code = """
def calculate_sum(a: int, b: int) -> int:
    \"\"\"Calculate the sum of two integers.\"\"\"
    return a + b

def process_items(items: list[int]) -> list[int]:
    result = []
    for item in items:
        if item > 0:
            result.append(item * 2)
    return result
"""
        report = d.detect(code, Path("test.py"))
        assert report.is_clean is True

    def test_detect_mixed_issues(self) -> None:
        d = AISlopDetector()
        code = """
def stub_function():
    pass

def risky_function():
    try:
""" + "        x = 1\n" * 55 + """    except:
        pass

if False:
    print("dead")
"""
        report = d.detect(code, Path("test.py"))
        assert report.score < 70
        categories = {f.category for f in report.findings}
        assert "empty_stub" in categories
        assert "silent_error_swallowing" in categories
        assert "dead_branch" in categories

    def test_detect_slop_convenience(self, tmp_path: Path) -> None:
        f = tmp_path / "test.py"
        f.write_text("try:\n    x = 1\nexcept:\n    pass\n", encoding="utf-8")
        report = detect_slop(f)
        assert len(report.findings) > 0

    def test_lines_analyzed(self) -> None:
        d = AISlopDetector()
        code = "x = 1\ny = 2\nz = 3\n"
        report = d.detect(code, Path("test.py"))
        assert report.lines_analyzed >= 3  # trailing newline may add 1

    def test_near_duplicate_blocks(self) -> None:
        d = AISlopDetector()
        code = "x = 1 + 2\ny = 1 + 3\nz = 1 + 4\nw = 1 + 5\n"
        # This might trigger near-duplicate detection
        report = d.detect(code, Path("test.py"))
        # At minimum, should not crash
        assert isinstance(report, SlopReport)

    def test_syntax_error_returns_empty_python_findings(self) -> None:
        """Lines 124-125: _check_python catches SyntaxError and returns empty findings."""
        d = AISlopDetector()
        code = "def foo(:\n    pass\n"
        report = d.detect(code, Path("test.py"))
        # Should not crash; python findings list is empty but generic checks still run
        assert isinstance(report, SlopReport)

    def test_redundant_none_check_then_truthiness(self) -> None:
        """Lines 184-188: redundant 'if x is not None' followed by 'if x'."""
        d = AISlopDetector()
        code = "if x is not None:\n    if x:\n        print(x)\n"
        report = d.detect(code, Path("test.py"))
        assert any(f.category == "redundant_check" for f in report.findings)

    def test_obvious_comment_restates_code(self) -> None:
        """Lines 302-310: comment that restates the following code line."""
        d = AISlopDetector()
        code = "# import os\nimport os\n"
        report = d.detect(code, Path("test.py"))
        assert any(f.category == "verbose_comment" and "restates" in f.message for f in report.findings)

    def test_obvious_comment_def(self) -> None:
        """Lines 302-310: 'def' comment restating a def line."""
        d = AISlopDetector()
        code = "# def my_function\ndef my_function():\n    pass\n"
        report = d.detect(code, Path("test.py"))
        assert any(f.category == "verbose_comment" and "restates" in f.message for f in report.findings)

    def test_main_block_with_file(self, tmp_path: Path) -> None:
        """Lines 321-329: __main__ block with a file argument."""
        import runpy
        import sys

        f = tmp_path / "sample.py"
        f.write_text("try:\n    x = 1\nexcept:\n    pass\n", encoding="utf-8")
        script = str(Path(__file__).resolve().parent.parent / "ai_slop_detector.py")
        old_argv = sys.argv
        sys.argv = [script, str(f)]
        try:
            runpy.run_path(script, run_name="__main__")
        finally:
            sys.argv = old_argv

    def test_main_block_else_branch(self, tmp_path: Path) -> None:
        """Lines 327-328: __main__ else branch (non-file path via mocked is_file)."""
        import runpy
        import sys
        from unittest.mock import patch

        f = tmp_path / "sample.py"
        f.write_text("x = 1\n", encoding="utf-8")
        script = str(Path(__file__).resolve().parent.parent / "ai_slop_detector.py")
        old_argv = sys.argv
        sys.argv = [script, str(f)]
        try:
            with patch.object(Path, "is_file", return_value=False):
                runpy.run_path(script, run_name="__main__")
        finally:
            sys.argv = old_argv
