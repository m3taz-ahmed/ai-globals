#!/usr/bin/env python3
"""Lightweight coding guardrails for aiZee.

Re-implements the Probity pattern: intercept file writes and shell commands
before they happen, match them against deterministic rules, and explain why
an action is blocked.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Final

from runtime.schemas import AizeeError, ErrorSeverity

# Action type aliases — normalize diverse action labels to canonical probity
# types so that rules matching "command"/"write"/"edit" also catch "Bash",
# "Shell", "Apply", "Patch", etc. (fixes GATE-02: "Bash" bypassed Probity).
ACTION_TYPE_ALIASES: Final[dict[str, str]] = {
    "bash": "exec",
    "shell": "exec",
    "command": "exec",
    "run": "exec",
    "cmd": "exec",
    "write": "write",
    "edit": "write",
    "apply": "write",
    "patch": "write",
    "save": "write",
}


def normalize_action_type(raw: str) -> str:
    """Normalize an action type to a canonical probity type.

    Maps case-insensitive aliases (e.g. "Bash" → "exec", "Apply" → "write")
    so that probity rules match regardless of the caller's naming convention.
    """
    t = raw.strip().lower()
    return ACTION_TYPE_ALIASES.get(t, t)


class GuardrailViolationError(AizeeError):
    """Raised when a coding rule is violated."""

    def __init__(self, rule_name: str, message: str) -> None:
        self.rule_name = rule_name
        self.message = message
        super().__init__(
            "GUARDRAIL_VIOLATION",
            f"Probity: {rule_name} - {message}",
            ErrorSeverity.HIGH,
            {"rule_name": rule_name},
        )


class GuardrailConfig:
    """Configuration for guardrail rules."""

    def __init__(self, rules: list[dict[str, Any]] | None = None) -> None:
        self.rules = rules or []


class GuardrailRule:
    """Base class for guardrail rules."""

    name: str = ""

    def check(self, event: dict[str, Any]) -> GuardrailViolationError | None:
        raise NotImplementedError  # pragma: no cover


class ForbidCommandPattern(GuardrailRule):
    """Block shell commands matching a regex."""

    def __init__(self, name: str, pattern: str, message: str) -> None:
        self.name = name
        self._pattern = re.compile(pattern)
        self._message = message

    def check(self, event: dict[str, Any]) -> GuardrailViolationError | None:
        command = event.get("command", "")
        if event.get("type") == "exec" and isinstance(command, str) and self._pattern.search(command):
            return GuardrailViolationError(self.name, self._message)
        return None


class RequireCommand(GuardrailRule):
    """Require a prior command before a later command."""

    def __init__(self, name: str, before: str, after: str, message: str) -> None:
        self.name = name
        self._before = re.compile(before)
        self._after = re.compile(after)
        self._message = message

    def check(self, event: dict[str, Any]) -> GuardrailViolationError | None:
        if event.get("type") != "exec":
            return None
        command = event.get("command", "")
        if not isinstance(command, str) or not self._after.search(command):
            return None
        history = event.get("history", [])
        for prior in reversed(history):
            if self._before.search(str(prior)):
                return None
        return GuardrailViolationError(self.name, self._message)


class ForbidContentPattern(GuardrailRule):
    """Block file writes that contain a regex."""

    def __init__(self, name: str, pattern: str, message: str) -> None:
        self.name = name
        self._pattern = re.compile(pattern)
        self._message = message

    def check(self, event: dict[str, Any]) -> GuardrailViolationError | None:
        if event.get("type") != "write":
            return None
        content = event.get("content", "")
        if isinstance(content, str) and self._pattern.search(content):
            return GuardrailViolationError(self.name, self._message)
        return None


class EnforceFilenameCasing(GuardrailRule):
    """Enforce a filename casing style."""

    def __init__(self, name: str, style: str, message: str) -> None:
        self.name = name
        self._style = style
        self._message = message

    def check(self, event: dict[str, Any]) -> GuardrailViolationError | None:
        if normalize_action_type(str(event.get("type", ""))) != "write":
            return None
        path = event.get("path", "")
        if not isinstance(path, str):
            return None
        name = Path(path).name
        if self._style == "kebab-case" and not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*\.[a-z]+$", name):
            return GuardrailViolationError(self.name, self._message)
        if self._style == "camelCase" and not re.match(r"^[a-z][a-zA-Z0-9]*\.[a-z]+$", name):
            return GuardrailViolationError(self.name, self._message)
        return None


class EnforceTdd(GuardrailRule):
    """Lightweight TDD reminder: a failing test should exist before production code."""

    name = "enforceTdd"

    def __init__(self, source_files: list[str], test_files: list[str]) -> None:
        self._source_pattern = re.compile("|".join(re.escape(p) for p in source_files))
        self._test_pattern = re.compile("|".join(re.escape(p) for p in test_files))

    def check(self, event: dict[str, Any]) -> GuardrailViolationError | None:
        if normalize_action_type(str(event.get("type", ""))) != "write":
            return None
        path = str(event.get("path", ""))
        if not self._source_pattern.search(path):
            return None
        history = event.get("history", [])
        for prior in reversed(history):
            if isinstance(prior, str) and self._test_pattern.search(prior):
                return None
        return GuardrailViolationError(
            self.name,
            "Add one focused test and run it to a clean assertion failure before production code.",
        )


def build_rule(config: dict[str, Any]) -> GuardrailRule | None:
    kind = config.get("kind")
    name = config.get("name", kind or "anonymous")
    if kind == "forbidCommandPattern":
        return ForbidCommandPattern(name, config["pattern"], config["message"])
    if kind == "requireCommand":
        return RequireCommand(name, config["before"], config["after"], config["message"])
    if kind == "forbidContentPattern":
        return ForbidContentPattern(name, config["pattern"], config["message"])
    if kind == "enforceFilenameCasing":
        return EnforceFilenameCasing(name, config["style"], config["message"])
    if kind == "enforceTdd":
        return EnforceTdd(config["source_files"], config["test_files"])
    return None


class Guardrails:
    """Collection of active guardrails."""

    def __init__(self, config: GuardrailConfig | dict[str, Any] | None = None) -> None:
        self.rules: list[GuardrailRule] = []
        cfg = GuardrailConfig(config.get("rules", [])) if isinstance(config, dict) else config
        if cfg:
            for rule_cfg in cfg.rules:
                rule = build_rule(rule_cfg)
                if rule:
                    self.rules.append(rule)

    def check(self, event: dict[str, Any]) -> None:
        # GATE-B2: Normalize action type before checking rules
        raw_type = event.get("type", "")
        if isinstance(raw_type, str):
            event = {**event, "type": normalize_action_type(raw_type)}
        for rule in self.rules:
            violation = rule.check(event)
            if violation:
                raise violation
