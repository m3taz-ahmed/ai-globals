"""Tests for runtime/output_gate.py — pre-send check + portability test.

FAST tier — no MCP, no kernel, no model loading.
"""

from __future__ import annotations

from runtime.output_gate import (
    auto_fix,
    check_output,
)


class TestCheckOutput:
    def test_clean_output_passes(self) -> None:
        result = check_output("Run `npm test` to verify the fix.\nNext: check the output.")
        assert result.passed is True

    def test_banned_opener_fails(self) -> None:
        result = check_output("Great question! The answer is 42.")
        assert result.passed is False
        assert any(i.category == "preamble" for i in result.issues)

    def test_banned_closer_fails(self) -> None:
        result = check_output("The fix is ready.\nLet me know if you need anything else.")
        assert result.passed is False
        assert any(i.category == "closer" for i in result.issues)

    def test_hedging_warning(self) -> None:
        result = check_output("This might possibly work.")
        assert result.warning_count >= 1
        assert any(i.category == "hedging" for i in result.issues)

    def test_idiom_warning(self) -> None:
        result = check_output("Let's circle back to this later.")
        assert result.warning_count >= 1
        assert any(i.category == "idiom" for i in result.issues)

    def test_portability_warning(self) -> None:
        result = check_output("This tool significantly improves engineering productivity.")
        assert result.warning_count >= 1
        assert any(i.category == "portability" for i in result.issues)

    def test_empty_text(self) -> None:
        result = check_output("")
        assert result.passed is True
        assert result.issues == []

    def test_first_last_line(self) -> None:
        result = check_output("Run `npm install`.\nThen edit the file.\nNext: run tests.")
        assert result.first_line == "Run `npm install`."
        assert result.last_line == "Next: run tests."


class TestAutoFix:
    def test_removes_opener(self) -> None:
        text = "Great question! The answer is 42."
        fixed, _remaining = auto_fix(text)
        assert "Great question" not in fixed
        assert "42" in fixed

    def test_removes_closer(self) -> None:
        text = "The fix is ready.\nLet me know if you need anything else."
        fixed, _remaining = auto_fix(text)
        assert "Let me know" not in fixed
        assert "fix is ready" in fixed

    def test_preserves_content(self) -> None:
        text = "Run `npm test`.\nThe output should be green."
        fixed, _remaining = auto_fix(text)
        assert "npm test" in fixed
        assert "green" in fixed

    def test_empty_text(self) -> None:
        fixed, remaining = auto_fix("")
        assert fixed == ""
        assert remaining == []
