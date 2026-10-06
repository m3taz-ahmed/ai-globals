"""Tests for runtime/mcp_manifest_lock.py — manifest fingerprinting."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest import mock

import pytest

from runtime.mcp_manifest_lock import ManifestFingerprint, ManifestLock
from runtime.schemas import AizeeError


@pytest.fixture()
def lock_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture()
def lock(lock_dir):
    return ManifestLock(lock_dir)


class TestLockAndVerify:
    def test_lock_creates_file(self, lock, lock_dir):
        fp = lock.lock("srv", "node srv.js", ["--x"], {"t": "desc"})
        assert (lock_dir / "srv.json").exists()
        assert fp.server_name == "srv"
        assert fp.locked_at

    def test_verify_clean(self, lock):
        lock.lock("srv", "cmd", ["a"], {"t": "d"})
        assert lock.verify("srv", "cmd", ["a"], {"t": "d"}) == []

    def test_verify_no_lock(self, lock):
        assert lock.verify("ghost", "cmd", [], {}) == []

    def test_command_drift(self, lock):
        lock.lock("srv", "cmd", [], {})
        f = lock.verify("srv", "cmd2", [], {})
        assert any(x["field"] == "command" and x["severity"] == "critical" for x in f)

    def test_args_drift(self, lock):
        lock.lock("srv", "cmd", ["a"], {})
        f = lock.verify("srv", "cmd", ["b"], {})
        assert any(x["field"] == "args" for x in f)

    def test_tool_desc_drift(self, lock):
        lock.lock("srv", "cmd", [], {"t": "orig"})
        f = lock.verify("srv", "cmd", [], {"t": "changed"})
        assert any("tools.t.description" in x["field"] for x in f)

    def test_tool_removed(self, lock):
        lock.lock("srv", "cmd", [], {"t1": "a", "t2": "b"})
        f = lock.verify("srv", "cmd", [], {"t1": "a"})
        assert any(x["field"] == "tools.t2" and x["severity"] == "high" for x in f)

    def test_tool_added_no_finding(self, lock):
        lock.lock("srv", "cmd", [], {"t1": "a"})
        f = lock.verify("srv", "cmd", [], {"t1": "a", "t2": "new"})
        assert f == []


class TestPersistence:
    def test_get_lock(self, lock):
        lock.lock("srv", "cmd", [], {"t": "d"}, locked_by="alice")
        fp = lock.get_lock("srv")
        assert fp.locked_by == "alice"

    def test_get_lock_missing(self, lock):
        assert lock.get_lock("ghost") is None

    def test_get_lock_corrupt(self, lock, lock_dir):
        (lock_dir / "bad.json").write_text("{corrupt")
        assert lock.get_lock("bad") is None

    def test_list_locks(self, lock):
        lock.lock("b_srv", "c", [], {})
        lock.lock("a_srv", "c", [], {})
        assert lock.list_locks() == ["a_srv", "b_srv"]

    def test_remove_lock(self, lock):
        lock.lock("srv", "c", [], {})
        assert lock.remove_lock("srv") is True
        assert lock.get_lock("srv") is None
        assert lock.remove_lock("srv") is False

    def test_name_sanitized(self, lock, lock_dir):
        lock.lock("a/b\\c", "cmd", [], {})
        assert (lock_dir / "a_b_c.json").exists()

    def test_write_failure_raises(self, lock):
        with mock.patch.object(Path, "write_text", side_effect=OSError("disk full")):
            with pytest.raises(AizeeError) as exc:
                lock.lock("srv", "c", [], {})
            assert exc.value.error_code == "MANIFEST_LOCK_WRITE_FAILED"


class TestFingerprint:
    def test_roundtrip(self):
        fp = ManifestFingerprint("s", "ch", "ah", {"t": "h"}, "2024-01-01", "bob")
        fp2 = ManifestFingerprint.from_dict(fp.to_dict())
        assert fp2.server_name == "s" and fp2.locked_by == "bob"
        assert fp2.tools_hash == {"t": "h"}

    def test_from_dict_defaults(self):
        fp = ManifestFingerprint.from_dict({
            "server_name": "s", "command_hash": "c", "args_hash": "a"})
        assert fp.tools_hash == {} and fp.locked_by is None

    def test_hash_determinism(self):
        fp1 = ManifestLock._hash_args(["b", "a"])
        fp2 = ManifestLock._hash_args(["b", "a"])
        assert fp1 == fp2
