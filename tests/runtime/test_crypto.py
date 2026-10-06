"""Tests for runtime/crypto.py — at-rest Fernet encryption utilities."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet

from runtime import crypto


@pytest.fixture(autouse=True)
def _isolate(monkeypatch, tmp_path):
    """Point all key env vars at tmp and clear them by default."""
    monkeypatch.delenv("AIOS_ENCRYPTION_KEY", raising=False)
    monkeypatch.delenv("AIOS_ENCRYPTION_KEY_FILE", raising=False)
    monkeypatch.setenv("AIZEE_ROOT", str(tmp_path))


class TestKeyResolution:
    def test_plaintext_opt_out(self, monkeypatch):
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY", "plaintext")
        assert crypto._get_fernet() is None

    def test_env_key(self, monkeypatch):
        key = Fernet.generate_key().decode()
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY", key)
        assert isinstance(crypto._get_fernet(), Fernet)

    def test_invalid_env_key(self, monkeypatch):
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY", "not-a-key")
        with pytest.raises(ValueError, match="not a valid Fernet key"):
            crypto._get_fernet()

    def test_key_file(self, monkeypatch, tmp_path):
        kf = tmp_path / "enc.key"
        kf.write_bytes(Fernet.generate_key())
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY_FILE", str(kf))
        assert isinstance(crypto._get_fernet(), Fernet)

    def test_key_file_empty(self, monkeypatch, tmp_path):
        kf = tmp_path / "enc.key"
        kf.write_bytes(b"")
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY_FILE", str(kf))
        with pytest.raises(ValueError, match="empty or missing"):
            crypto._get_fernet()

    def test_key_file_invalid_contents(self, monkeypatch, tmp_path):
        kf = tmp_path / "enc.key"
        kf.write_bytes(b"garbage-not-fernet")
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY_FILE", str(kf))
        with pytest.raises(ValueError, match="does not contain a valid Fernet key"):
            crypto._get_fernet()

    def test_key_file_missing(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY_FILE", str(tmp_path / "nope.key"))
        with pytest.raises(ValueError, match="empty or missing"):
            crypto._get_fernet()

    def test_autogenerate_key(self, tmp_path):
        f = crypto._get_fernet()
        assert isinstance(f, Fernet)
        key_path = tmp_path / "state" / ".encryption_key"
        assert key_path.is_file()
        # second call reuses stored key — roundtrip proof
        f2 = crypto._get_fernet()
        token = f.encrypt(b"hi")
        assert f2.decrypt(token) == b"hi"

    def test_stored_invalid_key_raises(self, tmp_path):
        key_path = tmp_path / "state" / ".encryption_key"
        key_path.parent.mkdir(parents=True)
        key_path.write_bytes(b"bad")
        with pytest.raises(ValueError, match="Stored encryption key"):
            crypto._get_fernet()


class TestEncryptDecryptBytes:
    def test_no_key_passthrough(self, monkeypatch):
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY", "plaintext")
        assert crypto.encrypt_bytes(b"data") == b"data"
        assert crypto.decrypt_bytes(b"data") == b"data"

    def test_roundtrip(self, monkeypatch):
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY", Fernet.generate_key().decode())
        enc = crypto.encrypt_bytes(b"secret")
        assert enc.startswith(b"AIOS_ENC:")
        assert crypto.decrypt_bytes(enc) == b"secret"

    def test_decrypt_plaintext_passthrough(self, monkeypatch):
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY", Fernet.generate_key().decode())
        assert crypto.decrypt_bytes(b"not encrypted") == b"not encrypted"

    def test_encrypted_but_no_key(self, monkeypatch):
        key = Fernet.generate_key().decode()
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY", key)
        enc = crypto.encrypt_bytes(b"x")
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY", "plaintext")
        with pytest.raises(ValueError, match="not set"):
            crypto.decrypt_bytes(enc)

    def test_wrong_key(self, monkeypatch):
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY", Fernet.generate_key().decode())
        enc = crypto.encrypt_bytes(b"x")
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY", Fernet.generate_key().decode())
        with pytest.raises(ValueError, match="Invalid encryption key"):
            crypto.decrypt_bytes(enc)


class TestFileOps:
    def test_is_encrypted(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY", Fernet.generate_key().decode())
        p = tmp_path / "f.txt"
        p.write_bytes(b"hello")
        assert crypto.is_encrypted(p) is False
        crypto.encrypt_file(p)
        assert crypto.is_encrypted(p) is True

    def test_is_encrypted_missing(self, tmp_path):
        assert crypto.is_encrypted(tmp_path / "nope") is False

    def test_is_encrypted_oserror(self, tmp_path, monkeypatch):
        p = tmp_path / "f"
        p.write_bytes(b"AIOS_ENC:x")
        with patch("builtins.open", side_effect=OSError("denied")):
            assert crypto.is_encrypted(p) is False

    def test_encrypt_file_no_key_noop(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY", "plaintext")
        p = tmp_path / "f.txt"
        p.write_bytes(b"hello")
        crypto.encrypt_file(p)
        assert p.read_bytes() == b"hello"

    def test_encrypt_file_missing_noop(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY", Fernet.generate_key().decode())
        crypto.encrypt_file(tmp_path / "gone")  # no error

    def test_encrypt_file_idempotent(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY", Fernet.generate_key().decode())
        p = tmp_path / "f.txt"
        p.write_bytes(b"hello")
        crypto.encrypt_file(p)
        first = p.read_bytes()
        crypto.encrypt_file(p)  # already encrypted — skip
        assert p.read_bytes() == first

    def test_decrypt_file_roundtrip(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY", Fernet.generate_key().decode())
        p = tmp_path / "f.txt"
        p.write_text("héllo wörld", encoding="utf-8")
        crypto.encrypt_file(p)
        assert crypto.decrypt_file(p) == "héllo wörld"

    def test_decrypt_file_plaintext(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY", "plaintext")
        p = tmp_path / "f.txt"
        p.write_text("plain", encoding="utf-8")
        assert crypto.decrypt_file(p) == "plain"

    def test_decrypt_file_missing(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            crypto.decrypt_file(tmp_path / "nope")

    def test_decrypt_file_not_utf8(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY", "plaintext")
        p = tmp_path / "f.bin"
        p.write_bytes(b"\xff\xfe\x00")
        with pytest.raises(ValueError, match="not valid UTF-8"):
            crypto.decrypt_file(p)


class TestGenerateKey:
    def test_generate_key_valid(self):
        key = crypto.generate_key()
        assert isinstance(Fernet(key.encode()), Fernet)
