#!/usr/bin/env python3
"""Tests for runtime.probity."""

from __future__ import annotations

import pytest

from runtime.probity import (
    EnforceFilenameCasing,
    EnforceTdd,
    ForbidCommandPattern,
    ForbidContentPattern,
    GuardrailConfig,
    Guardrails,
    GuardrailViolationError,
    RequireCommand,
    build_rule,
)


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


# ---------------------------------------------------------------------------
# RequireCommand — line 67 (non-command event returns None)
# ---------------------------------------------------------------------------

def test_require_command_non_command_event():
    """RequireCommand.check returns None for non-command events."""
    rule = RequireCommand("test", r"\bpytest\b", r"\bgit\s+commit\b", "msg")
    assert rule.check({"type": "write", "command": "git commit", "history": []}) is None


# ---------------------------------------------------------------------------
# RequireCommand — line 70 (command doesn't match 'after' pattern)
# ---------------------------------------------------------------------------

def test_require_command_after_not_matched():
    """RequireCommand.check returns None when command doesn't match the 'after' pattern."""
    rule = RequireCommand("test", r"\bpytest\b", r"\bgit\s+commit\b", "msg")
    assert rule.check({"type": "command", "command": "ls -la", "history": []}) is None


def test_require_command_non_string_command():
    """RequireCommand.check returns None when command is not a string."""
    rule = RequireCommand("test", r"\bpytest\b", r"\bgit\s+commit\b", "msg")
    assert rule.check({"type": "command", "command": 123, "history": []}) is None


# ---------------------------------------------------------------------------
# ForbidContentPattern — line 88 (non-write event returns None)
# ---------------------------------------------------------------------------

def test_forbid_content_non_write_event():
    """ForbidContentPattern.check returns None for non-write events."""
    rule = ForbidContentPattern("test", r"\beval\(", "msg")
    assert rule.check({"type": "command", "command": "eval(1)", "content": ""}) is None


# ---------------------------------------------------------------------------
# ForbidContentPattern — line 92 (content doesn't match returns None)
# ---------------------------------------------------------------------------

def test_forbid_content_no_match():
    """ForbidContentPattern.check returns None when content doesn't match."""
    rule = ForbidContentPattern("test", r"\beval\(", "msg")
    assert rule.check({"type": "write", "path": "x.py", "content": "print('hello')"}) is None


# ---------------------------------------------------------------------------
# EnforceFilenameCasing — line 105 (non-write/edit event returns None)
# ---------------------------------------------------------------------------

def test_enforce_casing_non_write_edit_event():
    """EnforceFilenameCasing.check returns None for non-write/edit events."""
    rule = EnforceFilenameCasing("test", "kebab-case", "msg")
    assert rule.check({"type": "command", "command": "ls", "path": "myFile.py"}) is None


# ---------------------------------------------------------------------------
# EnforceFilenameCasing — line 108 (non-string path returns None)
# ---------------------------------------------------------------------------

def test_enforce_casing_non_string_path():
    """EnforceFilenameCasing.check returns None when path is not a string."""
    rule = EnforceFilenameCasing("test", "kebab-case", "msg")
    assert rule.check({"type": "write", "path": 123, "content": ""}) is None


# ---------------------------------------------------------------------------
# EnforceFilenameCasing — lines 112-114 (camelCase style)
# ---------------------------------------------------------------------------

def test_enforce_casing_camelcase_violation():
    """camelCase style rejects non-camelCase filenames."""
    rule = EnforceFilenameCasing("test", "camelCase", "msg")
    assert rule.check({"type": "write", "path": "my-file.py", "content": ""}) is not None


def test_enforce_casing_camelcase_pass():
    """camelCase style accepts valid camelCase filenames."""
    rule = EnforceFilenameCasing("test", "camelCase", "msg")
    assert rule.check({"type": "write", "path": "myFile.py", "content": ""}) is None


def test_enforce_casing_kebabcase_pass():
    """kebab-case style accepts valid kebab-case filenames."""
    rule = EnforceFilenameCasing("test", "kebab-case", "msg")
    assert rule.check({"type": "write", "path": "my-file.py", "content": ""}) is None


def test_enforce_casing_edit_event():
    """EnforceFilenameCasing checks 'edit' events too."""
    rule = EnforceFilenameCasing("test", "kebab-case", "msg")
    assert rule.check({"type": "edit", "path": "myFile.py", "content": ""}) is not None


# ---------------------------------------------------------------------------
# EnforceTdd — lines 123-124, 127-136
# ---------------------------------------------------------------------------

def test_enforce_tdd_non_write_edit_event():
    """EnforceTdd.check returns None for non-write/edit events."""
    rule = EnforceTdd(["src/"], ["test_"])
    assert rule.check({"type": "command", "command": "ls", "path": "src/app.py"}) is None


def test_enforce_tdd_source_not_matched():
    """EnforceTdd.check returns None when path doesn't match source pattern."""
    rule = EnforceTdd(["src/"], ["test_"])
    assert rule.check({"type": "write", "path": "docs/readme.md", "content": ""}) is None


def test_enforce_tdd_violation_no_test_in_history():
    """EnforceTdd.check raises violation when no test in history."""
    rule = EnforceTdd(["src/"], ["test_"])
    violation = rule.check({"type": "write", "path": "src/app.py", "content": "", "history": ["src/other.py"]})
    assert violation is not None
    assert violation.rule_name == "enforceTdd"


def test_enforce_tdd_pass_with_test_in_history():
    """EnforceTdd.check returns None when a test exists in history."""
    rule = EnforceTdd(["src/"], ["test_"])
    assert rule.check({"type": "write", "path": "src/app.py", "content": "", "history": ["test_app.py"]}) is None


def test_enforce_tdd_empty_history():
    """EnforceTdd.check raises violation when history is empty."""
    rule = EnforceTdd(["src/"], ["test_"])
    violation = rule.check({"type": "write", "path": "src/app.py", "content": "", "history": []})
    assert violation is not None


def test_enforce_tdd_edit_event():
    """EnforceTdd.check checks 'edit' events too."""
    rule = EnforceTdd(["src/"], ["test_"])
    violation = rule.check({"type": "edit", "path": "src/app.py", "content": "", "history": []})
    assert violation is not None


# ---------------------------------------------------------------------------
# build_rule — lines 153-155 (enforceTdd kind and unknown kind)
# ---------------------------------------------------------------------------

def test_build_rule_enforce_tdd():
    """build_rule creates EnforceTdd from config."""
    rule = build_rule({
        "kind": "enforceTdd",
        "source_files": ["src/"],
        "test_files": ["test_"],
    })
    assert rule is not None
    assert isinstance(rule, EnforceTdd)


def test_build_rule_unknown_kind_returns_none():
    """build_rule returns None for unknown kind."""
    rule = build_rule({"kind": "unknown", "name": "test"})
    assert rule is None


def test_build_rule_no_kind_returns_none():
    """build_rule returns None when kind is missing."""
    rule = build_rule({"name": "test"})
    assert rule is None


# ---------------------------------------------------------------------------
# Guardrails with None config and GuardrailConfig
# ---------------------------------------------------------------------------

def test_guardrails_with_none_config():
    """Guardrails with None config has no rules."""
    g = Guardrails(None)
    assert g.rules == []
    g.check({"type": "command", "command": "rm -rf /"})  # should not raise


def test_guardrails_with_guardrail_config():
    """Guardrails accepts a GuardrailConfig object."""
    config = GuardrailConfig(rules=[{
        "kind": "forbidCommandPattern",
        "name": "no-rm",
        "pattern": r"\brm\s+-rf\b",
        "message": "no rm -rf",
    }])
    g = Guardrails(config)
    assert len(g.rules) == 1
    with pytest.raises(GuardrailViolationError):
        g.check({"type": "command", "command": "rm -rf /"})


# ---------------------------------------------------------------------------
# ForbidCommandPattern — non-command event and non-matching
# ---------------------------------------------------------------------------

def test_forbid_command_non_command_event():
    """ForbidCommandPattern.check returns None for non-command events."""
    rule = ForbidCommandPattern("test", r"\brm\s+-rf\b", "msg")
    assert rule.check({"type": "write", "command": "rm -rf /"}) is None


def test_forbid_command_non_string_command():
    """ForbidCommandPattern.check returns None when command is not a string."""
    rule = ForbidCommandPattern("test", r"\brm\s+-rf\b", "msg")
    assert rule.check({"type": "command", "command": 123}) is None


def test_forbid_command_no_match():
    """ForbidCommandPattern.check returns None when command doesn't match."""
    rule = ForbidCommandPattern("test", r"\brm\s+-rf\b", "msg")
    assert rule.check({"type": "command", "command": "ls -la"}) is None
