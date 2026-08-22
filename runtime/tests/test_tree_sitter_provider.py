"""Tests for runtime/tree_sitter_provider.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from runtime.tree_sitter_provider import (
    PythonASTExtractor,
    Symbol,
    SymbolProvider,
)

SAMPLE_PY = '''"""Sample module."""

def top_level_func(a, b):
    """A top-level function."""
    return a + b

class MyClass:
    """A sample class."""

    def my_method(self, x):
        """A method."""
        return x * 2

async def async_func():
    """An async function."""
    pass
'''


class TestSymbol:
    def test_symbol_defaults(self) -> None:
        # Arrange & Act
        sym = Symbol(name="foo", kind="function", file_path="test.py", line=1, end_line=5)

        # Assert
        assert sym.signature == ""
        assert sym.docstring == ""

    def test_symbol_stores_all_fields(self) -> None:
        # Arrange & Act
        sym = Symbol(
            name="foo", kind="function", file_path="m.py",
            line=10, end_line=20, signature="(a, b)", docstring="Does foo",
        )

        # Assert
        assert sym.name == "foo"
        assert sym.kind == "function"
        assert sym.line == 10
        assert sym.end_line == 20
        assert sym.signature == "(a, b)"
        assert sym.docstring == "Does foo"


class TestPythonASTExtractor:
    def test_extract_finds_top_level_function(self) -> None:
        # Arrange
        extractor = PythonASTExtractor()

        # Act
        symbols = extractor.extract(SAMPLE_PY, Path("test.py"))

        # Assert
        names = [s.name for s in symbols]
        assert "top_level_func" in names

    def test_extract_finds_class(self) -> None:
        # Arrange
        extractor = PythonASTExtractor()

        # Act
        symbols = extractor.extract(SAMPLE_PY, Path("test.py"))

        # Assert
        names = [s.name for s in symbols]
        assert "MyClass" in names

    def test_extract_finds_method_inside_class(self) -> None:
        # Arrange
        extractor = PythonASTExtractor()

        # Act
        symbols = extractor.extract(SAMPLE_PY, Path("test.py"))

        # Assert
        names = [s.name for s in symbols]
        assert "my_method" in names

    def test_extract_finds_async_function(self) -> None:
        # Arrange
        extractor = PythonASTExtractor()

        # Act
        symbols = extractor.extract(SAMPLE_PY, Path("test.py"))

        # Assert
        names = [s.name for s in symbols]
        assert "async_func" in names

    def test_extract_class_has_class_kind(self) -> None:
        # Arrange
        extractor = PythonASTExtractor()

        # Act
        symbols = extractor.extract(SAMPLE_PY, Path("test.py"))

        # Assert
        class_syms = [s for s in symbols if s.name == "MyClass"]
        assert len(class_syms) == 1
        assert class_syms[0].kind == "class"

    def test_extract_function_has_signature(self) -> None:
        # Arrange
        extractor = PythonASTExtractor()

        # Act
        symbols = extractor.extract(SAMPLE_PY, Path("test.py"))

        # Assert
        func = next(s for s in symbols if s.name == "top_level_func")
        assert "a" in func.signature
        assert "b" in func.signature

    def test_extract_function_has_docstring(self) -> None:
        # Arrange
        extractor = PythonASTExtractor()

        # Act
        symbols = extractor.extract(SAMPLE_PY, Path("test.py"))

        # Assert
        func = next(s for s in symbols if s.name == "top_level_func")
        assert "top-level function" in func.docstring

    def test_extract_syntax_error_returns_empty(self) -> None:
        # Arrange
        extractor = PythonASTExtractor()

        # Act
        symbols = extractor.extract("def broken(:\n    pass\n", Path("bad.py"))

        # Assert
        assert symbols == []

    def test_extract_empty_source_returns_empty(self) -> None:
        # Arrange
        extractor = PythonASTExtractor()

        # Act
        symbols = extractor.extract("", Path("empty.py"))

        # Assert
        assert symbols == []


class TestSymbolProvider:
    def test_extract_symbols_from_python_file(self, tmp_path: Path) -> None:
        # Arrange
        py_file = tmp_path / "sample.py"
        py_file.write_text(SAMPLE_PY, encoding="utf-8")
        provider = SymbolProvider()

        # Act
        symbols = provider.extract_symbols(py_file)

        # Assert
        names = [s.name for s in symbols]
        assert "top_level_func" in names
        assert "MyClass" in names

    def test_extract_symbols_unsupported_extension_returns_empty(self, tmp_path: Path) -> None:
        # Arrange
        txt_file = tmp_path / "readme.txt"
        txt_file.write_text("hello", encoding="utf-8")
        provider = SymbolProvider()

        # Act
        symbols = provider.extract_symbols(txt_file)

        # Assert
        assert symbols == []

    def test_extract_symbols_nonexistent_file_returns_empty(self) -> None:
        # Arrange
        provider = SymbolProvider()

        # Act
        symbols = provider.extract_symbols(Path("nonexistent.py"))

        # Assert
        assert symbols == []

    def test_register_custom_extractor(self, tmp_path: Path) -> None:
        # Arrange
        js_file = tmp_path / "app.js"
        js_file.write_text("function foo() {}", encoding="utf-8")
        provider = SymbolProvider()
        mock_extractor = MagicMock()
        mock_extractor.extract.return_value = [
            Symbol(name="foo", kind="function", file_path=str(js_file), line=1, end_line=1),
        ]

        # Act
        provider.register_extractor(".js", mock_extractor)
        symbols = provider.extract_symbols(js_file)

        # Assert
        assert len(symbols) == 1
        assert symbols[0].name == "foo"
        mock_extractor.extract.assert_called_once()

    def test_extract_from_directory_finds_all_files(self, tmp_path: Path) -> None:
        # Arrange
        (tmp_path / "a.py").write_text("def func_a():\n    pass\n", encoding="utf-8")
        (tmp_path / "b.py").write_text("def func_b():\n    pass\n", encoding="utf-8")
        provider = SymbolProvider()

        # Act
        symbols = provider.extract_from_directory(tmp_path)

        # Assert
        names = [s.name for s in symbols]
        assert "func_a" in names
        assert "func_b" in names

    def test_extract_from_directory_skips_pycache(self, tmp_path: Path) -> None:
        # Arrange
        (tmp_path / "a.py").write_text("def func_a():\n    pass\n", encoding="utf-8")
        pycache = tmp_path / "__pycache__"
        pycache.mkdir()
        (pycache / "cached.py").write_text("def cached():\n    pass\n", encoding="utf-8")
        provider = SymbolProvider()

        # Act
        symbols = provider.extract_from_directory(tmp_path)

        # Assert
        names = [s.name for s in symbols]
        assert "func_a" in names
        assert "cached" not in names
