"""Gap tests for runtime/crypto.py — key resolution order and error paths."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet

from runtime.crypto import (
    _get_fernet,
    decrypt_bytes,
    decrypt_file,
    encrypt_bytes,
    encrypt_file,
    generate_key,
    is_encrypted,
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch, tmp_path):
    for v in ("AIOS_ENCRYPTION_KEY", "AIOS_ENCRYPTION_KEY_FILE"):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setenv("AIZEE_ROOT", str(tmp_path))


@pytest.fixture
def key() -> bytes:
    return Fernet.generate_key()


class TestKeyResolution:
    def test_plaintext_optout(self, monkeypatch):
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY", "plaintext")
        assert _get_fernet() is None

    def test_env_key(self, monkeypatch, key):
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY", key.decode())
        assert isinstance(_get_fernet(), Fernet)

    def test_env_key_invalid(self, monkeypatch):
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY", "not-a-key")
        with pytest.raises(ValueError, match="not a valid Fernet key"):
            _get_fernet()

    def test_key_file(self, monkeypatch, tmp_path, key):
        kf = tmp_path / "ext.key"
        kf.write_bytes(key)
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY_FILE", str(kf))
        assert isinstance(_get_fernet(), Fernet)

    def test_key_file_empty(self, monkeypatch, tmp_path):
        kf = tmp_path / "ext.key"
        kf.write_bytes(b"")
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY_FILE", str(kf))
        with pytest.raises(ValueError, match="empty or missing"):
            _get_fernet()

    def test_key_file_missing(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY_FILE", str(tmp_path / "gone"))
        with pytest.raises(ValueError, match="empty or missing"):
            _get_fernet()

    def test_key_file_bad_key(self, monkeypatch, tmp_path):
        kf = tmp_path / "ext.key"
        kf.write_bytes(b"junk")
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY_FILE", str(kf))
        with pytest.raises(ValueError, match="does not contain a valid"):
            _get_fernet()

    def test_key_file_read_oserror(self, monkeypatch, tmp_path):
        kf = tmp_path / "ext.key"
        kf.write_bytes(b"x")
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY_FILE", str(kf))
        with patch.object(Path, "read_bytes", side_effect=OSError("denied")):
            with pytest.raises(ValueError, match="Cannot read"):
                _get_fernet()

    def test_autogen_creates_key(self, tmp_path):
        f = _get_fernet()
        assert isinstance(f, Fernet)
        kf = tmp_path / "state" / ".encryption_key"
        assert kf.is_file()
        # second call reads stored
        assert isinstance(_get_fernet(), Fernet)

    def test_autogen_stored_invalid(self, tmp_path):
        kf = tmp_path / "state" / ".encryption_key"
        kf.parent.mkdir(parents=True)
        kf.write_bytes(b"bogus")
        with pytest.raises(ValueError, match="invalid"):
            _get_fernet()

    def test_autogen_stored_read_oserror(self, tmp_path, monkeypatch):
        kf = tmp_path / "state" / ".encryption_key"
        kf.parent.mkdir(parents=True)
        kf.write_bytes(Fernet.generate_key())
        orig = Path.read_bytes
        calls = {"n": 0}

        def flaky(self, *a, **k):
            if self.name == ".encryption_key" and calls["n"] == 0:
                calls["n"] += 1
                raise OSError("flaky")
            return orig(self, *a, **k)

        monkeypatch.setattr(Path, "read_bytes", flaky)
        # stored read fails → treated as absent → generates a fresh key
        assert isinstance(_get_fernet(), Fernet)

    def test_autogen_race_lost_reads_winner(self, tmp_path, key):
        kf = tmp_path / "state" / ".encryption_key"
        kf.parent.mkdir(parents=True)
        kf.write_bytes(key)  # winner already wrote
        with patch("os.open", side_effect=FileExistsError):
            f = _get_fernet()
        assert isinstance(f, Fernet)

    def test_autogen_race_empty(self, tmp_path):
        kf = tmp_path / "state" / ".encryption_key"
        kf.parent.mkdir(parents=True)
        kf.write_bytes(b"")
        with patch("os.open", side_effect=FileExistsError):
            with pytest.raises(ValueError, match="empty"):
                _get_fernet()

    def test_autogen_race_read_oserror(self, tmp_path):
        kf = tmp_path / "state" / ".encryption_key"
        kf.parent.mkdir(parents=True)
        kf.write_bytes(Fernet.generate_key())
        with patch("os.open", side_effect=FileExistsError), \
             patch.object(Path, "read_bytes", side_effect=OSError("io")):
            with pytest.raises(ValueError, match="Cannot read raced"):
                _get_fernet()

    def test_autogen_create_oserror(self, tmp_path):
        with patch("os.open", side_effect=OSError("perm")):
            with pytest.raises(ValueError, match="Cannot create"):
                _get_fernet()

    def test_autogen_write_oserror(self, tmp_path, monkeypatch):
        import os as _os
        real_open = _os.open

        def open_ok(path, flags, mode=0o777):
            return real_open(path, flags & ~_os.O_EXCL, mode)

        monkeypatch.setattr(_os, "open", open_ok)
        with patch("os.fdopen", side_effect=OSError("disk full")):
            with pytest.raises((ValueError, OSError)):
                _get_fernet()

    def test_autogen_getlogin_fallback(self, tmp_path, monkeypatch):
        import os as _os
        monkeypatch.setattr(_os, "getlogin",
                            lambda: (_ for _ in ()).throw(OSError("x")))
        assert isinstance(_get_fernet(), Fernet)

    def test_autogen_acl_exception_fallback(self, tmp_path, monkeypatch):
        import subprocess as _sp
        monkeypatch.setattr(_sp, "run",
                            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no icacls")))
        assert isinstance(_get_fernet(), Fernet)


class TestRoundtrip:
    def test_encrypt_decrypt_bytes(self, monkeypatch, key):
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY", key.decode())
        enc = encrypt_bytes(b"secret")
        assert enc.startswith(b"AIOS_ENC:")
        assert decrypt_bytes(enc) == b"secret"

    def test_plaintext_passthrough(self, monkeypatch):
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY", "plaintext")
        assert encrypt_bytes(b"data") == b"data"
        assert decrypt_bytes(b"data") == b"data"

    def test_decrypt_non_magic(self, monkeypatch, key):
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY", key.decode())
        assert decrypt_bytes(b"plain") == b"plain"

    def test_decrypt_encrypted_no_key(self, monkeypatch):
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY", "plaintext")
        with pytest.raises(ValueError, match="not set"):
            decrypt_bytes(b"AIOS_ENC:xxx")

    def test_decrypt_bad_token(self, monkeypatch, key):
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY", key.decode())
        with pytest.raises(ValueError, match="corrupted"):
            decrypt_bytes(b"AIOS_ENC:garbage")

    def test_is_encrypted(self, monkeypatch, tmp_path, key):
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY", key.decode())
        f = tmp_path / "f.txt"
        f.write_bytes(b"data")
        assert is_encrypted(f) is False
        encrypt_file(f)
        assert is_encrypted(f) is True
        assert is_encrypted(tmp_path / "missing") is False
        assert is_encrypted(tmp_path) is False  # directory

    def test_encrypt_file_idempotent(self, monkeypatch, tmp_path, key):
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY", key.decode())
        f = tmp_path / "f.txt"
        f.write_text("hello")
        encrypt_file(f)
        first = f.read_bytes()
        encrypt_file(f)  # already encrypted → no-op
        assert f.read_bytes() == first
        encrypt_file(tmp_path / "missing")  # no-op

    def test_encrypt_file_no_key(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY", "plaintext")
        f = tmp_path / "f.txt"
        f.write_text("plain")
        encrypt_file(f)
        assert f.read_text() == "plain"

    def test_decrypt_file_roundtrip(self, monkeypatch, tmp_path, key):
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY", key.decode())
        f = tmp_path / "f.txt"
        f.write_text("hello world")
        encrypt_file(f)
        assert decrypt_file(f) == "hello world"

    def test_decrypt_file_missing(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            decrypt_file(tmp_path / "nope")

    def test_decrypt_file_read_oserror(self, monkeypatch, tmp_path, key):
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY", key.decode())
        f = tmp_path / "f.txt"
        f.write_text("x")
        with patch.object(Path, "read_bytes", side_effect=OSError("io")):
            with pytest.raises(ValueError, match="Cannot read"):
                decrypt_file(f)

    def test_decrypt_file_non_utf8(self, monkeypatch, tmp_path, key):
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY", key.decode())
        f = tmp_path / "f.bin"
        f.write_bytes(b"\xff\xfe\x00bad")
        with pytest.raises(ValueError, match="UTF-8"):
            decrypt_file(f)

    def test_generate_key(self):
        k = generate_key()
        assert isinstance(k, str)
        Fernet(k.encode())  # valid
