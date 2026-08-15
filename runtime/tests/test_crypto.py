"""Tests for runtime.crypto encryption utilities."""

from __future__ import annotations

from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from runtime.crypto import (
    decrypt_bytes,
    decrypt_file,
    encrypt_bytes,
    encrypt_file,
    generate_key,
    is_encrypted,
)


class TestEncryptDecrypt:
    def test_encrypt_decrypt_roundtrip(self, monkeypatch: pytest.MonkeyPatch) -> None:
        key = Fernet.generate_key().decode()
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY", key)
        original = b"hello world"
        encrypted = encrypt_bytes(original)
        assert encrypted != original
        assert is_encrypted_bytes(encrypted)
        decrypted = decrypt_bytes(encrypted)
        assert decrypted == original

    def test_no_key_returns_plaintext(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("AIOS_ENCRYPTION_KEY", raising=False)
        original = b"hello world"
        result = encrypt_bytes(original)
        assert result == original
        assert decrypt_bytes(result) == original

    def test_decrypt_without_key_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        key = Fernet.generate_key().decode()
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY", key)
        encrypted = encrypt_bytes(b"secret")
        monkeypatch.delenv("AIOS_ENCRYPTION_KEY", raising=False)
        with pytest.raises(ValueError, match="AIOS_ENCRYPTION_KEY"):
            decrypt_bytes(encrypted)

    def test_decrypt_invalid_key_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        key1 = Fernet.generate_key().decode()
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY", key1)
        encrypted = encrypt_bytes(b"secret")
        key2 = Fernet.generate_key().decode()
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY", key2)
        with pytest.raises(ValueError, match="Invalid encryption key"):
            decrypt_bytes(encrypted)


class TestFileEncryption:
    def test_encrypt_file_roundtrip(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        key = Fernet.generate_key().decode()
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY", key)
        f = tmp_path / "data.json"
        f.write_text('{"budget": 100}', encoding="utf-8")
        assert not is_encrypted(f)
        encrypt_file(f)
        assert is_encrypted(f)
        content = decrypt_file(f)
        assert content == '{"budget": 100}'

    def test_encrypt_file_no_key_is_noop(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("AIOS_ENCRYPTION_KEY", raising=False)
        f = tmp_path / "data.json"
        f.write_text('{"budget": 100}', encoding="utf-8")
        encrypt_file(f)
        assert not is_encrypted(f)
        assert f.read_text(encoding="utf-8") == '{"budget": 100}'

    def test_encrypt_file_already_encrypted_is_noop(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        key = Fernet.generate_key().decode()
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY", key)
        f = tmp_path / "data.json"
        f.write_text('{"budget": 100}', encoding="utf-8")
        encrypt_file(f)
        size_after_first = f.stat().st_size
        encrypt_file(f)
        assert f.stat().st_size == size_after_first

    def test_decrypt_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            decrypt_file(tmp_path / "nonexistent.json")


class TestGenerateKey:
    def test_generate_key_is_valid_fernet(self) -> None:
        key = generate_key()
        Fernet(key.encode())


class TestIsEncrypted:
    def test_nonexistent_file_returns_false(self, tmp_path: Path) -> None:
        """Cover line 38: is_encrypted returns False for nonexistent path."""
        assert is_encrypted(tmp_path / "missing.json") is False


def is_encrypted_bytes(data: bytes) -> bool:
    """Check if bytes start with the encryption magic prefix."""
    return data.startswith(b"AIOS_ENC:")
