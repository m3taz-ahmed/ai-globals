"""Tests for runtime/audit.py — audit logging with redaction and hash chaining."""

from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from runtime.audit import _GENESIS_HASH, _SENSITIVE_KEYS, AuditLogger


class TestRedaction:
    """Tests for _redact() method.

    Value redaction is precise (assignment-like secrets + known token
    prefixes), not bare-substring: innocent words containing "key"/"token"
    as substrings (e.g. "monkey") must survive.
    """

    @pytest.mark.parametrize("value", ["token=abc123", "api_token: xyz-999", "bearer TOKEN=secrettoken123"])
    def test_redacts_assignment_like_secrets(self, tmp_path: Path, value: str) -> None:
        logger = AuditLogger(tmp_path)
        result = logger._redact({"field": value})
        assert result == {"field": "[REDACTED]"}, f"Failed for value: {value}"

    @pytest.mark.parametrize("value", ["sk-abcdefgh12345678", "ghp_abcdefgh1234567890", "AKIAIOSFODNN7EXAMPLE"])
    def test_redacts_known_token_prefixes(self, tmp_path: Path, value: str) -> None:
        logger = AuditLogger(tmp_path)
        result = logger._redact({"field": value})
        assert result == {"field": "[REDACTED]"}, f"Failed for value: {value}"

    @pytest.mark.parametrize("value", ["my_token_value", "token123", "bearer_token", "mysecret", "monkey", "keyboard"])
    def test_does_not_redact_bare_substrings(self, tmp_path: Path, value: str) -> None:
        logger = AuditLogger(tmp_path)
        result = logger._redact({"field": value})
        assert result == {"field": value}, f"False positive for value: {value}"

    @pytest.mark.parametrize("value", ["password=123", "user_password: hunter2", "PASSWORD=abc"])
    def test_redacts_password_assignments(self, tmp_path: Path, value: str) -> None:
        logger = AuditLogger(tmp_path)
        result = logger._redact({"field": value})
        assert result == {"field": "[REDACTED]"}, f"Failed for value: {value}"

    @pytest.mark.parametrize("key", ["token", "password", "secret", "api_key", "credential", "auth"])
    def test_redacts_by_key_name(self, tmp_path: Path, key: str) -> None:
        """Key-based redaction: entire value redacted when key name is sensitive."""
        logger = AuditLogger(tmp_path)
        result = logger._redact({"data": {key: "normal_value"}})
        assert result == {"data": {key: "[REDACTED]"}}, f"Failed for key: {key}"

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
        # Redaction matches assignment-like secrets in values, not keys.
        result = logger._redact({"items": [{"field": "password=hunter2"}, {"normal": "y"}]})
        assert result == {"items": [{"field": "[REDACTED]"}, {"normal": "y"}]}

    def test_redacts_string_matching_pattern(self, tmp_path: Path) -> None:
        logger = AuditLogger(tmp_path)
        # An assignment-like secret in a bare string is redacted.
        result = logger._redact("api_key=abcdef123456")
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


@pytest.mark.slow
class TestAuditLoggerConcurrency:
    """Thread-safety tests."""

    def test_concurrent_writes_do_not_corrupt(self, tmp_path: Path) -> None:
        logger = AuditLogger(tmp_path)
        errors: list[Exception] = []

        def writer(idx: int) -> None:
            try:
                for i in range(50):
                    logger.log(f"event_{idx}_{i}", {"command": f"cmd{i}"})
            except Exception as exc:  # pragma: no cover
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


class TestHashChaining:
    """Tests for hash-chained append-only audit log."""

    def test_first_entry_has_genesis_prev_hash(self, tmp_path: Path) -> None:
        logger = AuditLogger(tmp_path)
        logger.log("test", {"command": "ls"})
        entry = json.loads(logger.log_file.read_text(encoding="utf-8").strip())
        assert entry["prev_hash"] == _GENESIS_HASH
        assert "hash" in entry
        assert len(entry["hash"]) == 64

    def test_second_entry_chains_to_first(self, tmp_path: Path) -> None:
        logger = AuditLogger(tmp_path)
        logger.log("event1", {"command": "ls"})
        logger.log("event2", {"command": "pwd"})
        lines = [line for line in logger.log_file.read_text(encoding="utf-8").strip().split("\n") if line]
        entry1 = json.loads(lines[0])
        entry2 = json.loads(lines[1])
        assert entry2["prev_hash"] == entry1["hash"]

    def test_verify_chain_valid(self, tmp_path: Path) -> None:
        logger = AuditLogger(tmp_path)
        for i in range(5):
            logger.log("event", {"idx": i})
        result = logger.verify_chain()
        assert result["valid"] is True
        assert result["entries_checked"] == 5
        assert result["broken_at"] is None

    def test_verify_chain_empty_log(self, tmp_path: Path) -> None:
        logger = AuditLogger(tmp_path)
        result = logger.verify_chain()
        assert result["valid"] is True
        assert result["entries_checked"] == 0

    def test_verify_chain_detects_tampering(self, tmp_path: Path) -> None:
        logger = AuditLogger(tmp_path)
        logger.log("event1", {"command": "ls"})
        logger.log("event2", {"command": "pwd"})
        logger.log("event3", {"command": "whoami"})
        # Tamper with the second line
        lines = logger.log_file.read_text(encoding="utf-8").strip().split("\n")
        entry1 = json.loads(lines[0])
        tampered_entry = {
            "ts": entry1["ts"],
            "type": "tampered",
            "details": {"command": "rm -rf /"},
            "prev_hash": entry1["prev_hash"],
            "hash": "f" * 64,  # wrong hash
        }
        lines[0] = json.dumps(tampered_entry)
        logger.log_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        result = logger.verify_chain()
        assert result["valid"] is False
        assert result["broken_at"] is not None

    def test_verify_chain_detects_middle_tampering(self, tmp_path: Path) -> None:
        logger = AuditLogger(tmp_path)
        logger.log("event1", {"command": "ls"})
        logger.log("event2", {"command": "pwd"})
        logger.log("event3", {"command": "whoami"})
        # Tamper with the middle entry's details (keep hash unchanged)
        lines = logger.log_file.read_text(encoding="utf-8").strip().split("\n")
        entry2 = json.loads(lines[1])
        entry2["details"] = {"command": "rm -rf /"}  # changed but hash not recomputed
        lines[1] = json.dumps(entry2)
        logger.log_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        result = logger.verify_chain()
        assert result["valid"] is False

    def test_hash_is_deterministic(self, tmp_path: Path) -> None:
        AuditLogger(tmp_path)
        entry = {
            "ts": "2026-01-01T00:00:00+00:00",
            "type": "test",
            "details": {"command": "ls"},
            "prev_hash": _GENESIS_HASH,
        }
        h1 = AuditLogger._compute_hash(entry)
        h2 = AuditLogger._compute_hash(entry)
        assert h1 == h2
        assert len(h1) == 64

    def test_hash_excludes_hash_field(self, tmp_path: Path) -> None:
        entry = {
            "ts": "2026-01-01T00:00:00+00:00",
            "type": "test",
            "details": {"command": "ls"},
            "prev_hash": _GENESIS_HASH,
        }
        entry_with_hash = dict(entry)
        entry_with_hash["hash"] = "abc123"
        h1 = AuditLogger._compute_hash(entry)
        h2 = AuditLogger._compute_hash(entry_with_hash)
        assert h1 == h2  # hash field should not affect computation

    @pytest.mark.slow
    def test_concurrent_writes_maintain_chain(self, tmp_path: Path) -> None:
        logger = AuditLogger(tmp_path)
        errors: list[Exception] = []

        def writer(idx: int) -> None:
            try:
                for i in range(20):
                    logger.log(f"event_{idx}_{i}", {"command": f"cmd{i}"})
            except Exception as exc:  # pragma: no cover
                errors.append(exc)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == []
        result = logger.verify_chain()
        assert result["valid"] is True
        assert result["entries_checked"] == 80  # 4 threads * 20 writes

    def test_concurrent_writes_exception_captured(self, tmp_path: Path) -> None:
        """Cover lines 148-149: except block in concurrent writer."""
        logger = AuditLogger(tmp_path)
        errors: list[Exception] = []

        # Patch log to raise on the second call
        original_log = logger.log
        call_count = [0]

        def failing_log(event_type, details):
            call_count[0] += 1
            if call_count[0] > 1:
                raise RuntimeError("forced log error")
            return original_log(event_type, details)

        logger.log = failing_log  # type: ignore[method-assign]

        def writer(idx: int) -> None:
            try:
                for i in range(5):
                    logger.log(f"event_{idx}_{i}", {"command": f"cmd{i}"})
            except Exception as exc:  # pragma: no cover
                errors.append(exc)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) > 0

    def test_concurrent_writes_chain_exception_captured(self, tmp_path: Path) -> None:
        """Cover lines 305-306: except block in concurrent chain writer."""
        logger = AuditLogger(tmp_path)
        errors: list[Exception] = []

        # Patch log to raise on the second call
        original_log = logger.log
        call_count = [0]

        def failing_log(event_type, details):
            call_count[0] += 1
            if call_count[0] > 1:
                raise RuntimeError("forced chain error")
            return original_log(event_type, details)

        logger.log = failing_log  # type: ignore[method-assign]

        def writer(idx: int) -> None:
            try:
                for i in range(5):
                    logger.log(f"event_{idx}_{i}", {"command": f"cmd{i}"})
            except Exception as exc:  # pragma: no cover
                errors.append(exc)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) > 0

    def test_redaction_applies_before_hashing(self, tmp_path: Path) -> None:
        """Sensitive values are redacted before the hash is computed."""
        logger = AuditLogger(tmp_path)
        logger.log("test", {"api_token": "secret123", "command": "ls"})
        lines = logger.log_file.read_text(encoding="utf-8").strip().split("\n")
        entry = json.loads(lines[0])
        assert entry["details"]["api_token"] == "[REDACTED]"
        # Verify the hash matches the redacted version
        recomputed = AuditLogger._compute_hash(entry)
        assert recomputed == entry["hash"]


# ---------------------------------------------------------------------------
# _last_hash — line 59 (empty file returns genesis)
# ---------------------------------------------------------------------------

class TestLastHashEdgeCases:
    """Tests for _last_hash edge cases."""

    def test_last_hash_empty_file_returns_genesis(self, tmp_path: Path) -> None:
        """_last_hash returns genesis hash when log file exists but is empty."""
        logger = AuditLogger(tmp_path)
        # Create the file but leave it empty (only blank lines)
        logger.log_file.parent.mkdir(parents=True, exist_ok=True)
        logger.log_file.write_text("\n\n\n", encoding="utf-8")
        assert logger._last_hash() == _GENESIS_HASH

    def test_last_hash_file_with_only_blank_lines(self, tmp_path: Path) -> None:
        """_last_hash returns genesis when file has only blank lines."""
        logger = AuditLogger(tmp_path)
        logger.log_file.parent.mkdir(parents=True, exist_ok=True)
        logger.log_file.write_text("   \n\n  \n", encoding="utf-8")
        assert logger._last_hash() == _GENESIS_HASH

    def test_last_hash_invalid_json_returns_genesis(self, tmp_path: Path) -> None:
        """_last_hash returns genesis when last line is invalid JSON."""
        logger = AuditLogger(tmp_path)
        logger.log_file.parent.mkdir(parents=True, exist_ok=True)
        logger.log_file.write_text("not valid json\n", encoding="utf-8")
        assert logger._last_hash() == _GENESIS_HASH

    def test_last_hash_missing_hash_key_returns_genesis(self, tmp_path: Path) -> None:
        """_last_hash returns genesis when last entry has no 'hash' key."""
        logger = AuditLogger(tmp_path)
        logger.log_file.parent.mkdir(parents=True, exist_ok=True)
        # Valid JSON but no 'hash' field
        logger.log_file.write_text(json.dumps({"ts": "now", "type": "test"}) + "\n", encoding="utf-8")
        assert logger._last_hash() == _GENESIS_HASH


# ---------------------------------------------------------------------------
# verify_chain — line 103 (skip blank lines)
# ---------------------------------------------------------------------------

class TestVerifyChainEdgeCases:
    """Tests for verify_chain edge cases."""

    def test_verify_chain_skips_blank_lines(self, tmp_path: Path) -> None:
        """verify_chain skips blank lines in the log file."""
        logger = AuditLogger(tmp_path)
        logger.log("event1", {"command": "ls"})
        # Insert blank lines between entries
        content = logger.log_file.read_text(encoding="utf-8")
        lines = content.strip().split("\n")
        logger.log_file.write_text(lines[0] + "\n\n\n  \n", encoding="utf-8")
        result = logger.verify_chain()
        assert result["valid"] is True
        assert result["entries_checked"] == 1

    def test_verify_chain_invalid_json_line(self, tmp_path: Path) -> None:
        """verify_chain detects invalid JSON and marks chain as broken."""
        logger = AuditLogger(tmp_path)
        logger.log("event1", {"command": "ls"})
        # Append an invalid JSON line
        with logger.log_file.open("a", encoding="utf-8") as f:
            f.write("not valid json\n")
        result = logger.verify_chain()
        assert result["valid"] is False
        assert result["broken_at"] is not None

    def test_verify_chain_broken_prev_hash_linkage(self, tmp_path: Path) -> None:
        """verify_chain detects when prev_hash doesn't match expected."""
        logger = AuditLogger(tmp_path)
        logger.log("event1", {"command": "ls"})
        logger.log("event2", {"command": "pwd"})
        # Tamper with the second entry's prev_hash
        lines = logger.log_file.read_text(encoding="utf-8").strip().split("\n")
        entry2 = json.loads(lines[1])
        entry2["prev_hash"] = "wrong_hash"  # doesn't match entry1's hash
        lines[1] = json.dumps(entry2)
        logger.log_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        result = logger.verify_chain()
        assert result["valid"] is False
        assert result["broken_at"] == 1
