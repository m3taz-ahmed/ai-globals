#!/usr/bin/env python3
"""Tests for runtime.probity."""

from __future__ import annotations

import pytest

from runtime.probity import Guardrails, GuardrailViolationError


def test_forbid_command_pattern():
    g = Guardrails(
        {
            "rules": [
                {
                    "kind": "forbidCommandPattern",
                    "name": "no-rm-rf",
                    "pattern": r"\brm\s+-rf\b",
                    "message": "Do not use rm -rf.",
                }
            ]
        }
    )
    g.check({"type": "command", "command": "ls"})
    with pytest.raises(GuardrailViolationError):
        g.check({"type": "command", "command": "rm -rf /"})


def test_forbid_content_pattern():
    g = Guardrails(
        {
            "rules": [
                {
                    "kind": "forbidContentPattern",
                    "name": "no-eval",
                    "pattern": r"\beval\(",
                    "message": "Do not use eval.",
                }
            ]
        }
    )
    with pytest.raises(GuardrailViolationError):
        g.check({"type": "write", "path": "x.py", "content": "eval('1+1')"})


def test_enforce_filename_casing():
    g = Guardrails(
        {
            "rules": [
                {
                    "kind": "enforceFilenameCasing",
                    "name": "kebab",
                    "style": "kebab-case",
                    "message": "Use kebab-case filenames.",
                }
            ]
        }
    )
    with pytest.raises(GuardrailViolationError):
        g.check({"type": "write", "path": "myFile.py", "content": ""})


def test_require_command():
    g = Guardrails(
        {
            "rules": [
                {
                    "kind": "requireCommand",
                    "name": "test-before-commit",
                    "before": r"\bpytest\b",
                    "after": r"\bgit\s+commit\b",
                    "message": "Run tests before committing.",
                }
            ]
        }
    )
    with pytest.raises(GuardrailViolationError):
        g.check({"type": "command", "command": "git commit -m x", "history": ["git add file.py"]})
    g.check({"type": "command", "command": "git commit -m x", "history": ["pytest"]})
