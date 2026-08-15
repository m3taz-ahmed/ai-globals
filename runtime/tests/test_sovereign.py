#!/usr/bin/env python3
"""Tests for runtime.sovereign."""

from __future__ import annotations

import pytest

from runtime.sovereign import AgentCapabilities, Capability, CapabilityStore


def test_grant_and_require():
    caps = AgentCapabilities()
    caps.grant(Capability("file.write", "project"))
    caps.require(Capability("file.write", "project"))
    with pytest.raises(PermissionError):
        caps.require(Capability("shell.exec", "project"))


def test_wildcard_grant():
    caps = AgentCapabilities()
    caps.grant(Capability("file.write"))
    caps.require(Capability("file.write", "project"))
    assert caps.list() == ["file.write:*"]


def test_revoke_removes_capability():
    """Cover line 37: CapabilityStore.revoke discards the capability string."""
    store = CapabilityStore()
    cap = Capability("file.write", "project")
    store.grant(cap)
    assert store.has(cap)
    store.revoke(cap)
    assert not store.has(cap)
