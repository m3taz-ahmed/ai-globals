#!/usr/bin/env python3
"""Tests for aios_mcp.adapters."""

from __future__ import annotations

import asyncio

import pytest

from aios_mcp.adapters import (
    AdapterError,
    Backend,
    LocalAdapter,
    default_registry,
)


def test_local_adapter_launch_and_poll():
    adapter = LocalAdapter()
    session = asyncio.run(adapter.launch("write tests", profile="tester"))
    assert session.backend == Backend.LOCAL
    assert session.profile == "tester"
    session = asyncio.run(adapter.poll(session))
    assert session.status == "completed"
    assert "result" in session.artifacts


def test_default_registry_runs_local():
    registry = default_registry()
    result = asyncio.run(registry.run(Backend.LOCAL, "write tests"))
    assert result["backend"] == "local"
    assert result["status"] == "completed"
    assert "result" in result["artifacts"]


def test_missing_adapter_raises():
    registry = default_registry()
    registry._adapters = {}
    with pytest.raises(AdapterError):
        asyncio.run(registry.run(Backend.LOCAL, "task"))
