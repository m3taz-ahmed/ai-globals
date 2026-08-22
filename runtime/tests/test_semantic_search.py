"""Tests for runtime/semantic_search.py."""

from __future__ import annotations

from pathlib import Path

from runtime.semantic_search import SearchResult, SemanticCodeSearch

SAMPLE_PY = '''"""Sample module for testing."""

def authenticate_user(username, password):
    """Authenticate a user by credentials."""
    return True

def fetch_data(query):
    """Fetch data from the database."""
    return []

class UserAuth:
    """User authentication handler."""
    pass
'''


class TestSearchResult:
    def test_search_result_defaults(self) -> None:
        # Arrange
        from runtime.codegraph import FunctionNode
        func = FunctionNode(name="test", file_path="test.py", line=1, end_line=5)

        # Act
        result = SearchResult(function=func, score=0.5)

        # Assert
        assert result.snippet == ""
        assert result.score == 0.5
        assert result.function.name == "test"


class TestSemanticCodeSearchIndexFile:
    def test_index_file_extracts_functions(self, tmp_path: Path) -> None:
        # Arrange
        py_file = tmp_path / "sample.py"
        py_file.write_text(SAMPLE_PY, encoding="utf-8")
        search = SemanticCodeSearch()

        # Act
        search.index_file(py_file)

        # Assert
        func_names = [f.name for f in search._functions]
        assert "authenticate_user" in func_names
        assert "fetch_data" in func_names

    def test_index_file_stores_snippets(self, tmp_path: Path) -> None:
        # Arrange
        py_file = tmp_path / "sample.py"
        py_file.write_text(SAMPLE_PY, encoding="utf-8")
        search = SemanticCodeSearch()

        # Act
        search.index_file(py_file)

        # Assert
        snippet = search._sources.get("authenticate_user", "")
        assert "authenticate_user" in snippet

    def test_index_file_handles_syntax_error(self, tmp_path: Path) -> None:
        # Arrange
        py_file = tmp_path / "bad.py"
        py_file.write_text("def broken(:\n    pass\n", encoding="utf-8")
        search = SemanticCodeSearch()

        # Act — should not raise
        search.index_file(py_file)

        # Assert — no functions indexed from invalid syntax
        assert len(search._functions) == 0


class TestSemanticCodeSearchSearch:
    def test_search_returns_results_matching_query(self, tmp_path: Path) -> None:
        # Arrange
        py_file = tmp_path / "sample.py"
        py_file.write_text(SAMPLE_PY, encoding="utf-8")
        search = SemanticCodeSearch()
        search.index_file(py_file)

        # Act
        results = search.search("authenticate user credentials")

        # Assert
        assert len(results) > 0
        assert results[0].function.name == "authenticate_user"

    def test_search_empty_index_returns_empty_list(self) -> None:
        # Arrange
        search = SemanticCodeSearch()

        # Act
        results = search.search("anything")

        # Assert
        assert results == []

    def test_search_empty_query_returns_empty_list(self, tmp_path: Path) -> None:
        # Arrange
        py_file = tmp_path / "sample.py"
        py_file.write_text(SAMPLE_PY, encoding="utf-8")
        search = SemanticCodeSearch()
        search.index_file(py_file)

        # Act
        results = search.search("")

        # Assert
        assert results == []

    def test_search_results_sorted_by_score_descending(self, tmp_path: Path) -> None:
        # Arrange
        py_file = tmp_path / "sample.py"
        py_file.write_text(SAMPLE_PY, encoding="utf-8")
        search = SemanticCodeSearch()
        search.index_file(py_file)

        # Act
        results = search.search("data fetch authenticate")

        # Assert
        if len(results) >= 2:
            assert results[0].score >= results[1].score

    def test_search_respects_limit(self, tmp_path: Path) -> None:
        # Arrange
        py_file = tmp_path / "sample.py"
        py_file.write_text(SAMPLE_PY, encoding="utf-8")
        search = SemanticCodeSearch()
        search.index_file(py_file)

        # Act
        results = search.search("data fetch authenticate", limit=1)

        # Assert
        assert len(results) <= 1

    def test_search_results_include_snippet(self, tmp_path: Path) -> None:
        # Arrange
        py_file = tmp_path / "sample.py"
        py_file.write_text(SAMPLE_PY, encoding="utf-8")
        search = SemanticCodeSearch()
        search.index_file(py_file)

        # Act
        results = search.search("authenticate")

        # Assert
        assert len(results) > 0
        assert results[0].snippet != ""

    def test_search_no_matching_tokens_returns_empty(self, tmp_path: Path) -> None:
        # Arrange
        py_file = tmp_path / "sample.py"
        py_file.write_text(SAMPLE_PY, encoding="utf-8")
        search = SemanticCodeSearch()
        search.index_file(py_file)

        # Act
        results = search.search("zzzzzzz")

        # Assert
        assert results == []


class TestSemanticCodeSearchIndexDirectory:
    def test_index_directory_indexes_py_files(self, tmp_path: Path) -> None:
        # Arrange
        (tmp_path / "a.py").write_text("def func_a():\n    pass\n", encoding="utf-8")
        (tmp_path / "b.py").write_text("def func_b():\n    pass\n", encoding="utf-8")
        search = SemanticCodeSearch()

        # Act
        search.index_directory(tmp_path)

        # Assert
        func_names = [f.name for f in search._functions]
        assert "func_a" in func_names
        assert "func_b" in func_names

    def test_index_directory_skips_pycache(self, tmp_path: Path) -> None:
        # Arrange
        (tmp_path / "a.py").write_text("def func_a():\n    pass\n", encoding="utf-8")
        pycache = tmp_path / "__pycache__"
        pycache.mkdir()
        (pycache / "cached.py").write_text("def cached():\n    pass\n", encoding="utf-8")
        search = SemanticCodeSearch()

        # Act
        search.index_directory(tmp_path)

        # Assert
        func_names = [f.name for f in search._functions]
        assert "func_a" in func_names
        assert "cached" not in func_names
