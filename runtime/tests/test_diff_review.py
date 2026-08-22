"""Tests for runtime/diff_review.py."""

from __future__ import annotations

from unittest.mock import MagicMock

from runtime.diff_review import DiffHunk, DiffParser, DiffReviewer

SAMPLE_DIFF = """--- a/test.py
+++ b/test.py
@@ -1,3 +1,4 @@
 def foo():
-    pass
+    x = None
+    if x == None:
+        return True
"""

EMPTY_DIFF = """--- a/empty.py
+++ b/empty.py
@@ -1,1 +1,1 @@
 same_line
"""


class TestDiffHunk:
    def test_default_fields_are_empty_lists(self) -> None:
        # Arrange & Act
        hunk = DiffHunk(file_path="test.py", old_start=1, new_start=1)

        # Assert
        assert hunk.added_lines == []
        assert hunk.removed_lines == []
        assert hunk.context_lines == []

    def test_hunk_stores_file_path_and_starts(self) -> None:
        # Arrange & Act
        hunk = DiffHunk(file_path="module.py", old_start=10, new_start=12)

        # Assert
        assert hunk.file_path == "module.py"
        assert hunk.old_start == 10
        assert hunk.new_start == 12


class TestDiffParserParse:
    def test_parse_single_hunk(self) -> None:
        # Act
        hunks = DiffParser.parse(SAMPLE_DIFF)

        # Assert
        assert len(hunks) == 1
        hunk = hunks[0]
        assert hunk.old_start == 1
        assert hunk.new_start == 1

    def test_parse_extracts_added_lines(self) -> None:
        # Act
        hunks = DiffParser.parse(SAMPLE_DIFF)

        # Assert
        hunk = hunks[0]
        added_contents = [line for _, line in hunk.added_lines]
        assert "    x = None" in added_contents
        assert "    if x == None:" in added_contents
        assert "        return True" in added_contents

    def test_parse_extracts_removed_lines(self) -> None:
        # Act
        hunks = DiffParser.parse(SAMPLE_DIFF)

        # Assert
        hunk = hunks[0]
        removed_contents = [line for _, line in hunk.removed_lines]
        assert "    pass" in removed_contents

    def test_parse_extracts_context_lines(self) -> None:
        # Act
        hunks = DiffParser.parse(SAMPLE_DIFF)

        # Assert
        hunk = hunks[0]
        context_contents = [line for _, line in hunk.context_lines]
        assert "def foo():" in context_contents

    def test_parse_empty_diff_returns_empty_list(self) -> None:
        # Act
        hunks = DiffParser.parse("")

        # Assert
        assert hunks == []

    def test_parse_multiple_hunks(self) -> None:
        # Arrange
        multi_diff = """--- a/a.py
+++ b/a.py
@@ -1,2 +1,3 @@
 line1
+added1
 line2
--- a/b.py
+++ b/b.py
@@ -5,2 +5,3 @@
 line5
+added2
 line6
"""

        # Act
        hunks = DiffParser.parse(multi_diff)

        # Assert
        assert len(hunks) == 2

    def test_parse_added_line_numbers_increment(self) -> None:
        # Act
        hunks = DiffParser.parse(SAMPLE_DIFF)

        # Assert — new_start is 1, so first added line should be line 2
        hunk = hunks[0]
        # Context line "def foo():" is at new_line 1, then added lines start at 2
        line_numbers = [num for num, _ in hunk.added_lines]
        assert line_numbers == [2, 3, 4]


class TestDiffParserExtractFilePaths:
    def test_extract_file_paths_from_b_prefix(self) -> None:
        # Act
        paths = DiffParser.extract_file_paths(SAMPLE_DIFF)

        # Assert
        assert paths == ["test.py"]

    def test_extract_file_paths_empty_diff(self) -> None:
        # Act
        paths = DiffParser.extract_file_paths("")

        # Assert
        assert paths == []

    def test_extract_file_paths_multiple_files(self) -> None:
        # Arrange
        diff = """--- a/a.py
+++ b/a.py
@@ -1,1 +1,1 @@
 x
--- a/b.py
+++ b/b.py
@@ -1,1 +1,1 @@
 y
"""

        # Act
        paths = DiffParser.extract_file_paths(diff)

        # Assert
        assert paths == ["a.py", "b.py"]


class TestDiffReviewer:
    def test_review_diff_returns_reports_for_hunks_with_additions(self) -> None:
        # Arrange
        reviewer = DiffReviewer()
        reviewer.engine = MagicMock()
        mock_report = MagicMock()
        mock_report.findings = []
        mock_report.passed = True
        reviewer.engine.review_diff.return_value = mock_report

        # Act
        reports = reviewer.review_diff(SAMPLE_DIFF)

        # Assert
        assert len(reports) == 1
        reviewer.engine.review_diff.assert_called_once()

    def test_review_diff_skips_hunks_without_added_lines(self) -> None:
        # Arrange
        reviewer = DiffReviewer()
        reviewer.engine = MagicMock()
        mock_report = MagicMock()
        mock_report.findings = []
        reviewer.engine.review_diff.return_value = mock_report

        # Act — EMPTY_DIFF has only context, no added lines
        reports = reviewer.review_diff(EMPTY_DIFF)

        # Assert
        assert reports == []
        reviewer.engine.review_diff.assert_not_called()

    def test_review_diff_summary_returns_dict(self) -> None:
        # Arrange
        reviewer = DiffReviewer()
        reviewer.engine = MagicMock()
        mock_report = MagicMock()
        mock_report.findings = []
        mock_report.passed = True
        mock_report.summary.return_value = {"file": "test.py", "passed": True}
        reviewer.engine.review_diff.return_value = mock_report

        # Act
        summary = reviewer.review_diff_summary(SAMPLE_DIFF)

        # Assert
        assert isinstance(summary, dict)
        assert "files_reviewed" in summary
        assert "total_findings" in summary
        assert "all_passed" in summary
        assert "reports" in summary

    def test_review_diff_summary_no_findings(self) -> None:
        # Arrange
        reviewer = DiffReviewer()
        reviewer.engine = MagicMock()
        mock_report = MagicMock()
        mock_report.findings = []
        mock_report.passed = True
        mock_report.summary.return_value = {}
        reviewer.engine.review_diff.return_value = mock_report

        # Act
        summary = reviewer.review_diff_summary(SAMPLE_DIFF)

        # Assert
        assert summary["total_findings"] == 0
        assert summary["all_passed"] is True
