"""Tests for plugin sandbox guard."""

from __future__ import annotations

import pytest

from runtime.plugin import PluginGuard, PluginSandboxError


def test_guard_blocks_denied() -> None:
    guard = PluginGuard(permissions=["Read", "Search"])
    assert guard.is_allowed("Read") is True
    assert guard.is_allowed("Bash") is False
    assert guard.is_allowed("Unknown") is False


def test_guard_wrap_blocks() -> None:
    guard = PluginGuard(permissions=["Read"])

    def tool(*, action: str):
        return action

    wrapped = guard.wrap(tool, "demo")
    assert wrapped(action="Read") == "Read"
    with pytest.raises(PluginSandboxError, match="blocked by sandbox"):
        wrapped(action="Bash")


def test_guard_allowed_empty() -> None:
    guard = PluginGuard()
    assert guard.is_allowed("Read") is True
    assert guard.is_allowed("Bash") is False
