#!/usr/bin/env python3
"""Tests for runtime.astryx."""

from __future__ import annotations

from runtime.astryx import AstryxLinter


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
