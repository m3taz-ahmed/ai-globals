"""Tests for audit.log_admission / log_authorization (Hazem identity keys)."""

from __future__ import annotations

import json
from pathlib import Path

from runtime.audit import AuditLogger


class TestLogAdmission:
    def test_log_admission_appends_entry(self, tmp_path: Path) -> None:
        logger = AuditLogger(tmp_path)
        logger.log_admission({
            "request_id": "r1",
            "context_hash": "sha256:abc",
            "runtime_key": "sha256:def",
            "output_key": "sha256:ghi",
            "stop_reason": "eos",
            "schema_valid": True,
            "evidence_coverage": 0.91,
            "policy_verdict": "allow",
            "admission_policy": "out-pol-14",
            "decision": "admit",
            "reason_code": "",
            "tenant_id": "t1",
        })
        lines = logger.log_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["type"] == "admission"
        assert entry["details"]["context_hash"] == "sha256:abc"
        assert entry["details"]["decision"] == "admit"
        assert entry["details"]["tenant_id"] == "t1"
        assert "prev_hash" in entry
        assert "hash" in entry

    def test_log_admission_redacts_sensitive(self, tmp_path: Path) -> None:
        logger = AuditLogger(tmp_path)
        logger.log_admission({
            "request_id": "r1",
            "context_hash": "my_secret_hash",  # contains "secret"
            "decision": "admit",
        })
        lines = logger.log_file.read_text(encoding="utf-8").strip().split("\n")
        entry = json.loads(lines[0])
        assert entry["details"]["context_hash"] == "[REDACTED]"

    def test_log_admission_chain_intact(self, tmp_path: Path) -> None:
        logger = AuditLogger(tmp_path)
        for i in range(3):
            logger.log_admission({"request_id": f"r{i}", "decision": "admit"})
        result = logger.verify_chain()
        assert result["valid"] is True
        assert result["entries_checked"] == 3


class TestLogAuthorization:
    def test_log_authorization_appends_entry(self, tmp_path: Path) -> None:
        logger = AuditLogger(tmp_path)
        logger.log_authorization({
            "decision_id": "dec-1",
            "tuple_hash": "sha256:abc",
            "subject_id": "u1",
            "tenant_id": "t1",
            "workload_id": "w1",
            "operation_id": "write",
            "target_id": "doc1",
            "decision": "allow",
            "reason": "",
            "obligations": ["require_receipt"],
            "idempotency_key": "idem-1",
            "receipt_id": "rcpt-1",
        })
        lines = logger.log_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["type"] == "authorization"
        assert entry["details"]["decision_id"] == "dec-1"
        assert entry["details"]["obligations"] == ["require_receipt"]

    def test_log_authorization_redacts_sensitive(self, tmp_path: Path) -> None:
        logger = AuditLogger(tmp_path)
        logger.log_authorization({
            "decision_id": "dec-1",
            "tuple_hash": "my_api_key_value",  # contains "api_key"
            "decision": "deny",
        })
        lines = logger.log_file.read_text(encoding="utf-8").strip().split("\n")
        entry = json.loads(lines[0])
        assert entry["details"]["tuple_hash"] == "[REDACTED]"

    def test_mixed_admission_and_authorization_chain(self, tmp_path: Path) -> None:
        logger = AuditLogger(tmp_path)
        logger.log_authorization({"decision_id": "dec-1", "decision": "allow"})
        logger.log_admission({"request_id": "r1", "decision": "admit"})
        result = logger.verify_chain()
        assert result["valid"] is True
        assert result["entries_checked"] == 2
