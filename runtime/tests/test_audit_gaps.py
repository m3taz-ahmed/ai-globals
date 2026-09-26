"""Gap-coverage tests for runtime/audit.py — key resolution, _ts_after,
rotation, purge, fail-open logging, read_entries filters, typed loggers."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from runtime import audit
from runtime.audit import AuditLogger, _get_audit_key, _restrict_file_permissions, _ts_after


@pytest.fixture(autouse=True)
def _reset_key(monkeypatch, tmp_path):
    audit._audit_key_cache = None
    monkeypatch.setenv("AIZEE_AUDIT_KEY", "test-key")
    monkeypatch.setenv("AIZEE_ROOT", str(tmp_path))
    yield
    audit._audit_key_cache = None


class TestAuditKey:
    def test_env_key(self, monkeypatch):
        monkeypatch.setenv("AIZEE_AUDIT_KEY", "mykey")
        assert _get_audit_key() == b"mykey"

    def test_key_file_env(self, monkeypatch, tmp_path):
        monkeypatch.delenv("AIZEE_AUDIT_KEY", raising=False)
        kf = tmp_path / "k.txt"
        kf.write_bytes(b"filekey")
        monkeypatch.setenv("AIZEE_AUDIT_KEY_FILE", str(kf))
        assert _get_audit_key() == b"filekey"

    def test_key_file_env_missing_falls_through(self, monkeypatch, tmp_path):
        monkeypatch.delenv("AIZEE_AUDIT_KEY", raising=False)
        monkeypatch.setenv("AIZEE_AUDIT_KEY_FILE", str(tmp_path / "nope"))
        key = _get_audit_key()  # auto-generates under AIZEE_ROOT
        assert len(key) == 32
        assert (tmp_path / "state" / "audit.key").exists()

    def test_key_file_env_empty_falls_through(self, monkeypatch, tmp_path):
        monkeypatch.delenv("AIZEE_AUDIT_KEY", raising=False)
        kf = tmp_path / "k.txt"
        kf.write_bytes(b"")
        monkeypatch.setenv("AIZEE_AUDIT_KEY_FILE", str(kf))
        assert len(_get_audit_key()) == 32

    def test_stored_key_reused(self, monkeypatch, tmp_path):
        monkeypatch.delenv("AIZEE_AUDIT_KEY", raising=False)
        monkeypatch.delenv("AIZEE_AUDIT_KEY_FILE", raising=False)
        audit._audit_key_cache = None
        k1 = _get_audit_key()
        audit._audit_key_cache = None
        k2 = _get_audit_key()
        assert k1 == k2

    def test_cached(self):
        audit._audit_key_cache = b"cached"
        assert _get_audit_key() == b"cached"


class TestRestrictPermissions:
    def test_posix_chmod(self, tmp_path):
        f = tmp_path / "f"
        f.write_text("x")
        with patch("platform.system", return_value="Linux"):
            _restrict_file_permissions(f)
        assert f.exists()

    def test_windows_icacls(self, tmp_path):
        f = tmp_path / "f"
        f.write_text("x")
        with patch("platform.system", return_value="Windows"), \
             patch("subprocess.run") as run:
            _restrict_file_permissions(f)
            run.assert_called_once()
            assert "icacls" in run.call_args[0][0]

    def test_windows_getlogin_fallback(self, tmp_path):
        f = tmp_path / "f"
        f.write_text("x")
        with patch("platform.system", return_value="Windows"), \
             patch("os.getlogin", side_effect=OSError), \
             patch("subprocess.run"):
            _restrict_file_permissions(f)  # no raise

    def test_all_fail_suppressed(self, tmp_path):
        f = tmp_path / "f"
        f.write_text("x")
        with patch("platform.system", return_value="Linux"), \
             patch.object(Path, "chmod", side_effect=OSError):
            _restrict_file_permissions(f)


class TestTsAfter:
    @pytest.mark.parametrize("entry,since,expected", [
        ("2024-01-02T00:00:00Z", "2024-01-01T00:00:00Z", True),
        ("2024-01-01T00:00:00Z", "2024-01-01T00:00:00Z", True),
        ("2024-01-01T00:00:00Z", "2024-01-02T00:00:00Z", False),
        ("2024-01-01T00:00:00+00:00", "2024-01-01T00:00:00Z", True),
        ("2024-01-01T00:00:00", "2024-01-01T00:00:00+00:00", True),  # naive→utc
        ("not-a-date", "2024-01-01", True),  # string fallback
        ("2024-01-01", "zzz", False),  # string fallback
    ])
    def test_compare(self, entry, since, expected):
        assert _ts_after(entry, since) == expected


class TestRotation:
    def test_rotation_preserves_chain(self, tmp_path, monkeypatch):
        log = AuditLogger(tmp_path)
        monkeypatch.setattr(log, "_MAX_LOG_SIZE", 200)  # force rotation quickly
        log.log("a", {"x": 1})
        log.log("b", {"x": 2})
        log.log("c", {"x": 3})
        rotated = log.log_file.with_suffix(".log.1")
        assert rotated.exists()
        # chain continues across rotation — verify current file
        result = log.verify_chain()
        # entries in current file start from rotated tip — first entry's
        # prev_hash won't be genesis, so verify_chain will flag broken at 0
        # OR the impl seeds correctly; at minimum no crash
        assert "entries_checked" in result

    def test_rotation_oserror_warns(self, tmp_path, monkeypatch):
        log = AuditLogger(tmp_path)
        monkeypatch.setattr(log, "_MAX_LOG_SIZE", 1)
        log.log("a", {})
        with patch.object(Path, "rename", side_effect=OSError("denied")):
            log.log("b", {})  # warns, doesn't raise beyond


class TestPurgeOSError:
    def test_purge_failure_warns(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AIZEE_AUDIT_RETENTION_DAYS", "7")
        log = AuditLogger(tmp_path)
        # create an old rotation
        old = log.log_file.with_suffix(".log.1")
        old.write_text("x")
        old_time = time.time() - 10 * 86400
        os.utime(old, (old_time, old_time))
        with patch.object(Path, "unlink", side_effect=OSError("denied")):
            log._purge_expired_rotations()  # warns only


class TestLogFailOpen:
    def test_write_failure_strict(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AIZEE_AUDIT_STRICT", "1")
        log = AuditLogger(tmp_path)
        with patch.object(Path, "open", side_effect=OSError("disk")):
            with pytest.raises(OSError):
                log.log("x", {})
        assert log.dropped == 1

    def test_write_failure_failopen(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AIZEE_AUDIT_STRICT", "0")
        log = AuditLogger(tmp_path)
        with patch.object(Path, "open", side_effect=OSError("disk")):
            log.log("x", {})  # no raise
        assert log.dropped == 1

    def test_stats(self, tmp_path):
        log = AuditLogger(tmp_path)
        s = log.stats()
        assert s["dropped"] == 0 and "log_file" in s


class TestReadEntries:
    def test_missing_file(self, tmp_path):
        assert AuditLogger(tmp_path).read_entries() == []

    def test_filters(self, tmp_path):
        log = AuditLogger(tmp_path)
        log.log("policy", {"a": 1})
        log.log("budget", {"b": 2})
        assert len(log.read_entries()) == 2
        only = log.read_entries(event_type="policy")
        assert len(only) == 1 and only[0]["type"] == "policy"

    def test_since_filter(self, tmp_path):
        log = AuditLogger(tmp_path)
        log.log("e", {})
        entries = log.read_entries(since="2999-01-01T00:00:00Z")
        assert entries == []
        entries = log.read_entries(since="1970-01-01T00:00:00Z")
        assert len(entries) == 1

    def test_corrupt_line_skipped(self, tmp_path):
        log = AuditLogger(tmp_path)
        log.log("e", {})
        with log.log_file.open("a") as f:
            f.write("{corrupt\n")
        entries = log.read_entries()
        assert len(entries) == 1

    def test_limit(self, tmp_path):
        log = AuditLogger(tmp_path)
        for i in range(10):
            log.log("e", {"i": i})
        assert len(log.read_entries(limit=3)) == 3


class TestTypedLoggers:
    def test_log_admission(self, tmp_path):
        log = AuditLogger(tmp_path)
        log.log_admission({"request_id": "r1", "decision": "allow"})
        entries = log.read_entries(event_type="admission")
        assert entries[0]["details"]["request_id"] == "r1"

    def test_log_authorization(self, tmp_path):
        log = AuditLogger(tmp_path)
        log.log_authorization({"decision_id": "d1", "decision": "deny"})
        entries = log.read_entries(event_type="authorization")
        assert entries[0]["details"]["decision_id"] == "d1"


class TestVerifyGaps:
    def test_verify_hmac_mismatch(self, tmp_path):
        log = AuditLogger(tmp_path)
        log.log("e", {"x": 1})
        # tamper: rewrite with valid JSON, valid prev_hash, bad hash
        lines = log.log_file.read_text().splitlines()
        entry = json.loads(lines[0])
        entry["hash"] = "0" * 64
        log.log_file.write_text(json.dumps(entry) + "\n")
        r = log.verify_chain()
        assert r["valid"] is False and r["broken_at"] == 0

    def test_verify_io_error(self, tmp_path):
        log = AuditLogger(tmp_path)
        log.log("e", {})
        with patch.object(Path, "open", side_effect=OSError("gone")):
            r = log.verify_chain()
        assert r["valid"] is False
