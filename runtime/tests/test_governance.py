#!/usr/bin/env python3
"""Tests for runtime.governance."""

from __future__ import annotations

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
