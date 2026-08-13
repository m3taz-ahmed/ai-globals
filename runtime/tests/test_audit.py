"""Tests for runtime/audit.py — audit logging with redaction."""

from __future__ import annotations

import json
import threading
from pathlib import Path

from runtime.audit import _SENSITIVE_KEYS, AuditLogger


class TestRedaction:
    """Tests for _redact() method."""

    def test_redacts_value_containing_token(self, tmp_path: Path) -> None:
        logger = AuditLogger(tmp_path)
        # Redaction matches against the VALUE string, not the key.
        result = logger._redact({"field": "my_token_value"})
        assert result == {"field": "[REDACTED]"}

    def test_redacts_value_containing_secret(self, tmp_path: Path) -> None:
        logger = AuditLogger(tmp_path)
        result = logger._redact({"field": "mysecret"})
        assert result == {"field": "[REDACTED]"}

    def test_redacts_value_containing_password(self, tmp_path: Path) -> None:
        logger = AuditLogger(tmp_path)
        result = logger._redact({"field": "password123"})
        assert result == {"field": "[REDACTED]"}

    def test_redacts_value_containing_credential(self, tmp_path: Path) -> None:
        logger = AuditLogger(tmp_path)
        result = logger._redact({"field": "credential_data"})
        assert result == {"field": "[REDACTED]"}

    def test_redacts_value_containing_auth(self, tmp_path: Path) -> None:
        logger = AuditLogger(tmp_path)
        result = logger._redact({"field": "auth_token"})
        assert result == {"field": "[REDACTED]"}

    def test_redacts_value_containing_api_key(self, tmp_path: Path) -> None:
        logger = AuditLogger(tmp_path)
        for val in ("api_key", "api-key", "apikey", "API_KEY"):
            result = logger._redact({"field": val})
            assert result == {"field": "[REDACTED]"}, f"Failed for value: {val}"

    def test_does_not_redact_normal_keys(self, tmp_path: Path) -> None:
        logger = AuditLogger(tmp_path)
        result = logger._redact({"command": "ls", "path": "/tmp"})
        assert result == {"command": "ls", "path": "/tmp"}

    def test_redacts_nested_dict(self, tmp_path: Path) -> None:
        logger = AuditLogger(tmp_path)
        result = logger._redact({"outer": {"inner_token": "secret"}})
        assert result == {"outer": {"inner_token": "[REDACTED]"}}

    def test_redacts_nested_list(self, tmp_path: Path) -> None:
        logger = AuditLogger(tmp_path)
        # Redaction matches against VALUE strings, not keys.
        result = logger._redact({"items": [{"field": "mysecret"}, {"normal": "y"}]})
        assert result == {"items": [{"field": "[REDACTED]"}, {"normal": "y"}]}

    def test_redacts_string_matching_pattern(self, tmp_path: Path) -> None:
        logger = AuditLogger(tmp_path)
        # The regex matches against the value, not just keys
        result = logger._redact("my_token_value")
        assert result == "[REDACTED]"

    def test_preserves_non_string_values(self, tmp_path: Path) -> None:
        logger = AuditLogger(tmp_path)
        result = logger._redact({"count": 42, "enabled": True, "ratio": 1.5})
        assert result == {"count": 42, "enabled": True, "ratio": 1.5}

    def test_handles_none_value(self, tmp_path: Path) -> None:
        logger = AuditLogger(tmp_path)
        result = logger._redact(None)
        assert result is None

    def test_handles_empty_dict(self, tmp_path: Path) -> None:
        logger = AuditLogger(tmp_path)
        result = logger._redact({})
        assert result == {}


class TestAuditLogging:
    """Tests for log() method and file output."""

    def test_creates_log_file(self, tmp_path: Path) -> None:
        logger = AuditLogger(tmp_path)
        logger.log("test_event", {"command": "ls"})
        assert logger.log_file.exists()

    def test_writes_valid_jsonl(self, tmp_path: Path) -> None:
        logger = AuditLogger(tmp_path)
        logger.log("event1", {"command": "ls"})
        logger.log("event2", {"command": "pwd"})
        content = logger.log_file.read_text(encoding="utf-8")
        lines = [line for line in content.strip().split("\n") if line]
        assert len(lines) == 2
        for line in lines:
            entry = json.loads(line)
            assert "ts" in entry
            assert "type" in entry
            assert "details" in entry

    def test_log_entry_has_timestamp(self, tmp_path: Path) -> None:
        logger = AuditLogger(tmp_path)
        logger.log("test", {"command": "ls"})
        entry = json.loads(logger.log_file.read_text(encoding="utf-8").strip())
        assert "ts" in entry
        assert "T" in entry["ts"]  # ISO format

    def test_log_entry_has_type(self, tmp_path: Path) -> None:
        logger = AuditLogger(tmp_path)
        logger.log("policy_check", {"command": "ls"})
        entry = json.loads(logger.log_file.read_text(encoding="utf-8").strip())
        assert entry["type"] == "policy_check"

    def test_redacts_sensitive_in_log(self, tmp_path: Path) -> None:
        logger = AuditLogger(tmp_path)
        logger.log("test", {"api_token": "secret123", "command": "ls"})
        entry = json.loads(logger.log_file.read_text(encoding="utf-8").strip())
        assert entry["details"]["api_token"] == "[REDACTED]"
        assert entry["details"]["command"] == "ls"

    def test_creates_state_dir_if_missing(self, tmp_path: Path) -> None:
        state_dir = tmp_path / "state"
        assert not state_dir.exists()
        logger = AuditLogger(tmp_path)
        logger.log("test", {"command": "ls"})
        assert state_dir.exists()


class TestAuditLoggerConcurrency:
    """Thread-safety tests."""

    def test_concurrent_writes_do_not_corrupt(self, tmp_path: Path) -> None:
        logger = AuditLogger(tmp_path)
        errors: list[Exception] = []

        def writer(idx: int) -> None:
            try:
                for i in range(50):
                    logger.log(f"event_{idx}_{i}", {"command": f"cmd{i}"})
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == []
        # Verify all lines are valid JSON
        content = logger.log_file.read_text(encoding="utf-8")
        lines = [line for line in content.strip().split("\n") if line]
        assert len(lines) == 400  # 8 threads * 50 writes
        for line in lines:
            json.loads(line)  # should not raise


class TestSensitiveKeysPattern:
    """Tests for the _SENSITIVE_KEYS regex."""

    def test_matches_token(self) -> None:
        assert _SENSITIVE_KEYS.search("api_token")

    def test_matches_key(self) -> None:
        assert _SENSITIVE_KEYS.search("secret_key")

    def test_matches_password(self) -> None:
        assert _SENSITIVE_KEYS.search("password")

    def test_matches_credential(self) -> None:
        assert _SENSITIVE_KEYS.search("credential")

    def test_matches_auth(self) -> None:
        assert _SENSITIVE_KEYS.search("auth")

    def test_matches_api_key_with_underscore(self) -> None:
        assert _SENSITIVE_KEYS.search("api_key")

    def test_matches_api_key_with_hyphen(self) -> None:
        assert _SENSITIVE_KEYS.search("api-key")

    def test_case_insensitive(self) -> None:
        assert _SENSITIVE_KEYS.search("TOKEN")
        assert _SENSITIVE_KEYS.search("Password")
        assert _SENSITIVE_KEYS.search("SECRET")

    def test_does_not_match_normal_words(self) -> None:
        assert not _SENSITIVE_KEYS.search("command")
        assert not _SENSITIVE_KEYS.search("path")
        assert not _SENSITIVE_KEYS.search("normal_field")
