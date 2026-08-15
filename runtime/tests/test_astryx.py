#!/usr/bin/env python3
"""Tests for runtime.astryx."""

from __future__ import annotations

from runtime.astryx import AstryxLinter, format_findings


def test_no_findings_on_clean_code():
    code = """
def add(a: int, b: int) -> int:
    return a + b
"""
    findings = AstryxLinter().lint_text(code)
    assert not findings


def test_bare_except():
    code = """
try:
    pass
except:
    pass
"""
    findings = AstryxLinter().lint_text(code)
    assert any(f.rule == "no-bare-except" for f in findings)


def test_mutable_default():
    code = "def f(x=[]): pass"
    findings = AstryxLinter().lint_text(code)
    assert any(f.rule == "no-mutable-default" for f in findings)


def test_eval():
    code = "eval('1+1')"
    findings = AstryxLinter().lint_text(code)
    assert any(f.rule == "no-eval" for f in findings)


def test_async_function_too_long():
    """Cover lines 38-39, 49: async function def that is too long."""
    lines = ["async def long_async():"] + ["    pass"] * 60
    code = "\n".join(lines) + "\n"
    findings = AstryxLinter(max_lines=50).lint_text(code)
    assert any(f.rule == "function-too-long" for f in findings)


def test_function_too_long():
    """Cover line 49: sync function that exceeds max_lines."""
    lines = ["def long_func():"] + ["    pass"] * 60
    code = "\n".join(lines) + "\n"
    findings = AstryxLinter(max_lines=50).lint_text(code)
    assert any(f.rule == "function-too-long" for f in findings)


def test_too_many_params_with_vararg_and_kwarg():
    """Cover lines 56, 58, 60: vararg, kwarg, and too-many-params detection."""
    code = "def f(a, b, c, d, e, f, g, h, *args, **kwargs): pass\n"
    findings = AstryxLinter(max_params=7).lint_text(code)
    assert any(f.rule == "too-many-params" for f in findings)


def test_syntax_error():
    """Cover lines 86-87: syntax error returns a finding."""
    code = "def f(:\n    pass\n"
    findings = AstryxLinter().lint_text(code)
    assert any(f.rule == "syntax-error" for f in findings)
    assert findings[0].severity == "error"


def test_format_findings_empty():
    """Cover lines 98-99: format_findings with no findings."""
    assert format_findings([]) == "No findings."


def test_format_findings_with_results():
    """Cover lines 100-103: format_findings renders findings."""
    from runtime.astryx import LintFinding

    findings = [
        LintFinding(rule="no-eval", line=1, message="Avoid eval()", severity="error"),
        LintFinding(rule="function-too-long", line=5, message="Too long", severity="warning"),
    ]
    result = format_findings(findings)
    assert "error: no-eval at line 1" in result
    assert "warning: function-too-long at line 5" in result
