"""Tests for runtime/tool_output_bounder.py — tool output bounding.

FAST tier — no MCP, no kernel, no model loading.
"""

from __future__ import annotations

import pytest

from runtime.tool_output_bounder import (
    AUDIT_BOUNDS,
    DEFAULT_BOUNDS,
    OutputBounds,
    bound_json_output,
    bound_output,
    bound_tool_result,
)


class TestBoundOutput:
    def test_short_output_unchanged(self) -> None:
        result = bound_output("Hello World")
        assert result.truncated is False
        assert result.text == "Hello World"

    def test_line_limit_truncation(self) -> None:
        lines = [f"Line {i}" for i in range(300)]
        output = "\n".join(lines)
        bounds = OutputBounds(max_lines=10, max_bytes=10000)
        result = bound_output(output, bounds)
        assert result.truncated is True
        assert result.original_lines == 300
        assert "truncated" in result.text

    def test_byte_limit_truncation(self) -> None:
        output = "A" * 10000
        bounds = OutputBounds(max_lines=10000, max_bytes=100)
        result = bound_output(output, bounds)
        assert result.truncated is True
        assert result.original_bytes == 10000

    def test_both_limits_line_wins(self) -> None:
        lines = [f"Line {i}" for i in range(500)]
        output = "\n".join(lines)
        bounds = OutputBounds(max_lines=10, max_bytes=100000)
        result = bound_output(output, bounds)
        assert result.truncated is True
        assert "line limit" in result.reason

    def test_empty_string(self) -> None:
        result = bound_output("")
        assert result.truncated is False
        assert result.text == ""

    def test_type_error(self) -> None:
        with pytest.raises(TypeError):
            bound_output(123)  # type: ignore[arg-type]

    def test_utf8_safe_truncation(self) -> None:
        # Multi-byte UTF-8 characters
        output = "مرحبا" * 1000  # Arabic, 2 bytes per char
        bounds = OutputBounds(max_lines=10000, max_bytes=50)
        result = bound_output(output, bounds)
        assert result.truncated is True
        # Should not contain replacement chars from split multi-byte
        assert "\ufffd" not in result.text or "truncated" in result.text


class TestBoundJsonOutput:
    def test_dict_serialization(self) -> None:
        result = bound_json_output({"key": "value"}, DEFAULT_BOUNDS)
        assert result.truncated is False
        assert "key" in result.text

    def test_large_dict_truncated(self) -> None:
        data = {str(i): "x" * 100 for i in range(1000)}
        result = bound_json_output(data, OutputBounds(max_lines=10, max_bytes=1000))
        assert result.truncated is True


class TestBoundToolResult:
    def test_string_result(self) -> None:
        result = bound_tool_result("Hello", "test_tool")
        assert "Hello" in result

    def test_dict_result(self) -> None:
        result = bound_tool_result({"data": "value"}, "test_tool")
        assert "data" in result

    def test_truncation_includes_tool_name(self) -> None:
        output = "A" * 10000
        result = bound_tool_result(output, "my_tool", OutputBounds(max_lines=10000, max_bytes=100))
        assert "my_tool" in result
        assert "truncated" in result


class TestOutputBounds:
    def test_default_bounds(self) -> None:
        assert DEFAULT_BOUNDS.max_lines == 200
        assert DEFAULT_BOUNDS.max_bytes == 8000

    def test_audit_bounds_larger(self) -> None:
        assert AUDIT_BOUNDS.max_lines > DEFAULT_BOUNDS.max_lines
        assert AUDIT_BOUNDS.max_bytes > DEFAULT_BOUNDS.max_bytes
