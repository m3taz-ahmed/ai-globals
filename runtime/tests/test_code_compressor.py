"""Tests for runtime/code_compressor.py — code compression."""

from __future__ import annotations

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
