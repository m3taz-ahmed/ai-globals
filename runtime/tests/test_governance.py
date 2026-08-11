#!/usr/bin/env python3
"""Tests for runtime.governance."""

from __future__ import annotations

import pytest

from runtime.audit import AuditLogger
from runtime.governance import GovernanceHooks
from runtime.telemetry import TelemetryCollector


def test_governance_hook_logs(tmp_path):
    audit = AuditLogger(tmp_path)
    telemetry = TelemetryCollector(tmp_path)
    hooks = GovernanceHooks(audit, telemetry)

    with hooks.around_action("test"):
        pass

    log_text = (tmp_path / "state" / "audit.log").read_text()
    assert '"type": "test"' in log_text
    events = telemetry.query(event_type="action")
    assert events[0]["action"] == "test"
    assert events[0]["status"] == "completed"


def test_governance_hook_records_failure(tmp_path):
    audit = AuditLogger(tmp_path)
    telemetry = TelemetryCollector(tmp_path)
    hooks = GovernanceHooks(audit, telemetry)

    with pytest.raises(ValueError, match="boom"), hooks.around_action("failing_action"):
        raise ValueError("boom")

    events = telemetry.query(event_type="action")
    assert events[0]["action"] == "failing_action"
    assert events[0]["status"] == "failed"
    assert "error" in events[0]["metadata"]


def test_governance_wrap_success(tmp_path):
    audit = AuditLogger(tmp_path)
    telemetry = TelemetryCollector(tmp_path)
    hooks = GovernanceHooks(audit, telemetry)

    def add(a: int, b: int) -> int:
        return a + b

    wrapped = hooks.wrap("wrapped_fn", add)
    result = wrapped(2, 3)
    assert result == 5
    events = telemetry.query(event_type="action")
    assert events[0]["action"] == "wrapped_fn"
    assert events[0]["status"] == "completed"


def test_governance_wrap_failure(tmp_path):
    audit = AuditLogger(tmp_path)
    telemetry = TelemetryCollector(tmp_path)
    hooks = GovernanceHooks(audit, telemetry)

    def boom() -> None:
        raise RuntimeError("kaboom")

    wrapped = hooks.wrap("wrapped_fail", boom)
    with pytest.raises(RuntimeError, match="kaboom"):
        wrapped()

    events = telemetry.query(event_type="action")
    assert events[0]["action"] == "wrapped_fail"
    assert events[0]["status"] == "failed"


def test_governance_around_action_with_kwargs(tmp_path):
    audit = AuditLogger(tmp_path)
    telemetry = TelemetryCollector(tmp_path)
    hooks = GovernanceHooks(audit, telemetry)

    with hooks.around_action("action_with_meta", user="alice", tool="grep"):
        pass

    events = telemetry.query(event_type="action")
    assert events[0]["metadata"]["user"] == "alice"
    assert events[0]["metadata"]["tool"] == "grep"
