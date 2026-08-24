"""Tests for audit fail-open behavior (from agent-observatory)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from runtime.audit import AuditLogger


def test_audit_log_fail_open_on_write_error(tmp_path: Path) -> None:
    logger = AuditLogger(tmp_path)
    # Mock the file open to raise OSError
    with patch("builtins.open", side_effect=OSError("disk full")):
        # Should NOT raise — fail-open
        logger.log("test_event", {"key": "value"})


def test_audit_log_normal_write(tmp_path: Path) -> None:
    logger = AuditLogger(tmp_path)
    logger.log("test_event", {"action": "exec", "result": "ok"})
    entries = logger.read_entries()
    assert len(entries) == 1
    assert entries[0]["type"] == "test_event"
    assert entries[0]["details"]["action"] == "exec"


def test_audit_log_redaction(tmp_path: Path) -> None:
    logger = AuditLogger(tmp_path)
    logger.log("test", {"api_key": "sk-12345", "safe": "ok"})
    entries = logger.read_entries()
    assert entries[0]["details"]["api_key"] == "[REDACTED]"
    assert entries[0]["details"]["safe"] == "ok"


def test_audit_chain_integrity(tmp_path: Path) -> None:
    logger = AuditLogger(tmp_path)
    logger.log("event1", {"a": 1})
    logger.log("event2", {"b": 2})
    result = logger.verify_chain()
    assert result["valid"] is True
    assert result["entries_checked"] == 2


def test_audit_log_admission(tmp_path: Path) -> None:
    logger = AuditLogger(tmp_path)
    logger.log_admission({
        "request_id": "req-1",
        "context_hash": "abc123",
        "runtime_key": "rk-1",
        "output_key": "ok-1",
        "stop_reason": "completed",
        "schema_valid": True,
        "evidence_coverage": 0.95,
        "policy_verdict": "allow",
        "admission_policy": "default",
        "decision": "admit",
        "reason_code": "",
        "tenant_id": "tenant-1",
    })
    entries = logger.read_entries(event_type="admission")
    assert len(entries) == 1
    assert entries[0]["details"]["request_id"] == "req-1"
    assert entries[0]["details"]["evidence_coverage"] == 0.95
