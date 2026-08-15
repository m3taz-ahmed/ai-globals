"""Tests for runtime/code_compressor.py — code compression."""

from __future__ import annotations

import sys
from pathlib import Path

from runtime.code_compressor import (
    CodeCompressor,
    CompressionResult,
    GenericCompressor,
    PythonCompressor,
    _estimate_tokens,
)


class TestEstimateTokens:
    """Tests for token estimation."""

    def test_empty_string(self) -> None:
        assert _estimate_tokens("") == 1

    def test_short_string(self) -> None:
        assert _estimate_tokens("hello") == 1  # 5 chars / 4 = 1.25 -> 1

    def test_long_string(self) -> None:
        assert _estimate_tokens("a" * 100) == 25  # 100 / 4 = 25


class TestCompressionResult:
    """Tests for CompressionResult."""

    def test_reduction_percent(self) -> None:
        r = CompressionResult("orig", "comp", original_tokens=100, compressed_tokens=30)
        assert r.reduction_percent == 70.0

    def test_reduction_percent_zero_original(self) -> None:
        r = CompressionResult("", "", original_tokens=0, compressed_tokens=0)
        assert r.reduction_percent == 0.0

    def test_reduction_ratio(self) -> None:
        r = CompressionResult("orig", "comp", original_tokens=100, compressed_tokens=30)
        assert "70.0%" in r.reduction_ratio


class TestPythonCompressor:
    """Tests for PythonCompressor."""

    def test_compress_simple_function(self) -> None:
        c = PythonCompressor()
        code = "def foo(x: int) -> str:\n    return str(x)\n"
        result = c.compress(code)
        assert "def foo(x: int) -> str: ..." in result.compressed_code
        assert result.compressed_tokens < result.original_tokens

    def test_compress_class(self) -> None:
        c = PythonCompressor()
        code = "class Bar:\n    def method(self):\n        return 1\n"
        result = c.compress(code)
        assert "class Bar: ..." in result.compressed_code
        assert "def method(self): ..." in result.compressed_code

    def test_compress_imports(self) -> None:
        c = PythonCompressor()
        code = "import os\nfrom pathlib import Path\n"
        result = c.compress(code)
        assert "import os" in result.compressed_code
        assert "from pathlib import Path" in result.compressed_code

    def test_compress_async_function(self) -> None:
        c = PythonCompressor()
        code = "async def fetch(url: str) -> bytes:\n    return b'data'\n"
        result = c.compress(code)
        assert "async def fetch" in result.compressed_code

    def test_compress_with_decorators(self) -> None:
        c = PythonCompressor()
        code = "@property\ndef value(self):\n    return self._value\n"
        result = c.compress(code)
        assert "@property" in result.compressed_code

    def test_compress_with_docstring(self) -> None:
        c = PythonCompressor()
        code = 'def foo():\n    """This is a docstring."""\n    return 1\n'
        result = c.compress(code)
        assert "This is a docstring" in result.compressed_code

    def test_compress_syntax_error_returns_original(self) -> None:
        c = PythonCompressor()
        code = "def foo(:\n"
        result = c.compress(code)
        assert result.compressed_code == code

    def test_compress_constants(self) -> None:
        c = PythonCompressor()
        code = "MAX_RETRIES = 3\nTIMEOUT = 30\n"
        result = c.compress(code)
        assert "MAX_RETRIES" in result.compressed_code

    def test_compress_class_with_bases(self) -> None:
        c = PythonCompressor()
        code = "class Dog(Animal):\n    pass\n"
        result = c.compress(code)
        assert "class Dog(Animal): ..." in result.compressed_code

    def test_compress_reduces_tokens(self) -> None:
        c = PythonCompressor()
        code = """
def complex_function(a: int, b: str, c: list[int]) -> dict[str, int]:
    result = {}
    for item in c:
        result[b + str(item)] = a + item
    return result

class DataProcessor:
    def __init__(self, config: dict):
        self.config = config

    def process(self, data: list) -> list:
        return [self.transform(item) for item in data]

    def transform(self, item):
        return item * 2
"""
        result = c.compress(code)
        assert result.reduction_percent > 30  # should reduce significantly


class TestGenericCompressor:
    """Tests for GenericCompressor."""

    def test_compress_javascript(self) -> None:
        c = GenericCompressor()
        code = "function foo(a, b) {\n  return a + b;\n}\n"
        result = c.compress(code, language="js")
        assert "function foo" in result.compressed_code

    def test_compress_js_class(self) -> None:
        c = GenericCompressor()
        code = "class MyComponent extends React.Component {\n  render() {}\n}\n"
        result = c.compress(code, language="js")
        assert "class MyComponent" in result.compressed_code

    def test_compress_imports(self) -> None:
        c = GenericCompressor()
        code = "import React from 'react';\nimport { useState } from 'react';\n"
        result = c.compress(code, language="js")
        assert "import" in result.compressed_code


class TestCodeCompressor:
    """Tests for CodeCompressor dispatch."""

    def test_compress_python_file(self, tmp_path: Path) -> None:
        f = tmp_path / "test.py"
        f.write_text("def foo():\n    return 1\n", encoding="utf-8")
        c = CodeCompressor()
        result = c.compress_file(f)
        assert result.language == "python"
        assert "def foo" in result.compressed_code

    def test_compress_js_file(self, tmp_path: Path) -> None:
        f = tmp_path / "test.js"
        f.write_text("function foo() { return 1; }\n", encoding="utf-8")
        c = CodeCompressor()
        result = c.compress_file(f)
        assert "function foo" in result.compressed_code

    def test_compress_nonexistent_file(self, tmp_path: Path) -> None:
        c = CodeCompressor()
        result = c.compress_file(tmp_path / "nonexistent.py")
        assert result.compressed_code == ""

    def test_compress_directory(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("def a():\n    pass\n", encoding="utf-8")
        (tmp_path / "b.py").write_text("def b():\n    pass\n", encoding="utf-8")
        c = CodeCompressor()
        results = c.compress_directory(tmp_path)
        assert len(results) == 2

    def test_compress_directory_excludes(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "config.py").write_text("x = 2\n", encoding="utf-8")
        c = CodeCompressor()
        results = c.compress_directory(tmp_path)
        assert len(results) == 1  # .git excluded

    def test_compress_to_context(self, tmp_path: Path) -> None:
        files = []
        for i in range(3):
            f = tmp_path / f"file{i}.py"
            f.write_text(f"def func{i}():\n    return {i}\n", encoding="utf-8")
            files.append(f)
        c = CodeCompressor()
        context = c.compress_to_context(files, max_tokens=1000)
        assert "file0" in context
        assert "file1" in context
        assert "file2" in context

    def test_compress_to_context_token_limit(self, tmp_path: Path) -> None:
        files = []
        for i in range(10):
            f = tmp_path / f"file{i}.py"
            f.write_text(f"def func{i}():\n    return {i}\n" * 20, encoding="utf-8")
            files.append(f)
        c = CodeCompressor()
        context = c.compress_to_context(files, max_tokens=100)
        # Should include at least the first file
        assert "file0" in context
        # Should not include all 10 files due to token limit
        assert "file9" not in context

    def test_compress_code_auto_detect_python(self) -> None:
        c = CodeCompressor()
        result = c.compress_code("def foo():\n    return 1\n")
        assert "def foo" in result.compressed_code

    def test_compress_code_with_path(self) -> None:
        c = CodeCompressor()
        result = c.compress_code("def foo():\n    return 1\n", Path("test.py"))
        assert result.language == "python"

    def test_compress_code_auto_detect_generic(self) -> None:
        """Code without 'def ' or 'import ' uses GenericCompressor."""
        c = CodeCompressor()
        result = c.compress_code("var x = 1;\n")
        assert result.language == ""

    # --- PythonCompressor: argument formatting branches ---

    def test_compress_vararg(self) -> None:
        c = PythonCompressor()
        result = c.compress("def foo(*args): ...\n")
        assert "*args" in result.compressed_code

    def test_compress_kwonly_with_star_sep(self) -> None:
        c = PythonCompressor()
        result = c.compress("def foo(a, *, b: int): ...\n")
        assert "*" in result.compressed_code
        assert "b: int" in result.compressed_code

    def test_compress_kwarg(self) -> None:
        c = PythonCompressor()
        result = c.compress("def foo(**kwargs): ...\n")
        assert "**kwargs" in result.compressed_code

    # --- PythonCompressor: class with docstring and decorator ---

    def test_compress_class_with_docstring(self) -> None:
        c = PythonCompressor()
        code = 'class Bar:\n    """A test class."""\n    pass\n'
        result = c.compress(code)
        assert "A test class" in result.compressed_code

    def test_compress_class_with_decorator(self) -> None:
        c = PythonCompressor()
        code = "from dataclasses import dataclass\n\n@dataclass\nclass Foo:\n    pass\n"
        result = c.compress(code)
        assert "@dataclass" in result.compressed_code

    # --- PythonCompressor: _format_expr branches ---

    def test_compress_attribute_annotation(self) -> None:
        """Attribute expression in type annotation."""
        c = PythonCompressor()
        code = "def foo(x: module.Type) -> None: ...\n"
        result = c.compress(code)
        assert "module.Type" in result.compressed_code

    def test_compress_call_value(self) -> None:
        """Call expression as a constant value."""
        c = PythonCompressor()
        code = "DEFAULT = func()\n"
        result = c.compress(code)
        assert "func(...)" in result.compressed_code

    def test_compress_binop_value(self) -> None:
        """BinOp expression as a constant value."""
        c = PythonCompressor()
        code = "TOTAL = 1 + 2\n"
        result = c.compress(code)
        assert "+" in result.compressed_code or "..." in result.compressed_code

    def test_compress_list_value(self) -> None:
        """List literal as a constant value."""
        c = PythonCompressor()
        code = "ITEMS = [1, 2, 3]\n"
        result = c.compress(code)
        assert "[" in result.compressed_code

    def test_compress_dict_value(self) -> None:
        """Dict literal as a constant value."""
        c = PythonCompressor()
        code = 'CONFIG = {"key": 1}\n'
        result = c.compress(code)
        assert "{" in result.compressed_code

    def test_compress_unhandled_expr_fallback(self) -> None:
        """Unhandled expression type (Set) falls back to '...'."""
        c = PythonCompressor()
        code = "_VALUES = {1, 2, 3}\n"
        result = c.compress(code)
        assert "..." in result.compressed_code

    # --- compress_directory: non-matching extension ---

    def test_compress_directory_skips_non_matching_ext(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("def a():\n    pass\n", encoding="utf-8")
        (tmp_path / "b.txt").write_text("not code\n", encoding="utf-8")
        c = CodeCompressor()
        results = c.compress_directory(tmp_path)
        assert len(results) == 1

    # --- __main__ block ---

    def test_main_block_file(self, tmp_path: Path, capsys) -> None:
        """Exercise __main__ block with a file target."""
        f = tmp_path / "test.py"
        f.write_text("def foo():\n    return 1\n", encoding="utf-8")
        source = Path(__file__).resolve().parent.parent / "code_compressor.py"
        code = source.read_text(encoding="utf-8")
        old_argv = sys.argv
        sys.argv = ["code_compressor.py", str(f)]
        try:
            exec(compile(code, str(source), "exec"), {"__name__": "__main__"})
        finally:
            sys.argv = old_argv
        out = capsys.readouterr().out
        assert "Language:" in out
        assert "Reduction:" in out

    def test_main_block_directory(self, tmp_path: Path, capsys) -> None:
        """Exercise __main__ block with a directory target."""
        (tmp_path / "a.py").write_text("def a():\n    pass\n", encoding="utf-8")
        source = Path(__file__).resolve().parent.parent / "code_compressor.py"
        code = source.read_text(encoding="utf-8")
        old_argv = sys.argv
        sys.argv = ["code_compressor.py", str(tmp_path)]
        try:
            exec(compile(code, str(source), "exec"), {"__name__": "__main__"})
        finally:
            sys.argv = old_argv
        out = capsys.readouterr().out
        assert "Files:" in out
        assert "Tokens:" in out
