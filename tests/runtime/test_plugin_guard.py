"""Tests for plugin sandbox guard."""

from __future__ import annotations

from runtime.plugin import PluginGuard


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
    try:
        wrapped(action="Bash")
    except RuntimeError:
        pass
    else:
        raise AssertionError("Expected RuntimeError")


def test_guard_allowed_empty() -> None:
    guard = PluginGuard()
    assert guard.is_allowed("Read") is True
    assert guard.is_allowed("Bash") is False
