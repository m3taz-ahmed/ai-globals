"""Tests for runtime/audit_signing.py — Ed25519/HMAC audit signatures."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest import mock

import pytest

import runtime.audit_signing as mod
from runtime.audit_signing import _HAS_CRYPTOGRAPHY, AuditSigner, SignatureScheme


@pytest.fixture()
def key_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


def _signer(key_dir: Path, monkeypatch) -> AuditSigner:
    monkeypatch.delenv("AIZEE_AUDIT_SIGN_KEY", raising=False)
    return AuditSigner(key_path=key_dir / "test_sign.key")


class TestSchemeSelection:
    def test_ed25519_when_crypto(self, key_dir, monkeypatch):
        if not _HAS_CRYPTOGRAPHY:
            pytest.skip("cryptography unavailable")
        s = _signer(key_dir, monkeypatch)
        assert s.scheme() is SignatureScheme.ED25519

    def test_hmac_fallback(self, key_dir, monkeypatch):
        monkeypatch.setattr(mod, "_HAS_CRYPTOGRAPHY", False)
        s = _signer(key_dir, monkeypatch)
        assert s.scheme() is SignatureScheme.HMAC_SHA512

    def test_env_key_path(self, key_dir, monkeypatch):
        env_key = key_dir / "env_key.pem"
        monkeypatch.setenv("AIZEE_AUDIT_SIGN_KEY", str(env_key))
        s = AuditSigner()
        # key file created at env path
        assert env_key.exists()
        assert s.scheme() in (SignatureScheme.ED25519, SignatureScheme.HMAC_SHA512)


class TestSignVerify:
    def test_roundtrip_ed25519(self, key_dir, monkeypatch):
        if not _HAS_CRYPTOGRAPHY:
            pytest.skip("cryptography unavailable")
        s = _signer(key_dir, monkeypatch)
        # sign() appends timestamp; verify() checks raw payload — the
        # docstring says callers include the timestamp. So sign then
        # verify the *signed_data* form.
        result = s.sign(b"payload")
        assert result.scheme is SignatureScheme.ED25519
        assert result.public_key is not None
        # Verify with timestamped payload
        signed_data = b"payload|" + str(result.timestamp).encode()
        assert s.verify(signed_data, result.signature, result.public_key) is True

    def test_roundtrip_hmac(self, key_dir, monkeypatch):
        monkeypatch.setattr(mod, "_HAS_CRYPTOGRAPHY", False)
        s = _signer(key_dir, monkeypatch)
        result = s.sign(b"payload")
        signed_data = b"payload|" + str(result.timestamp).encode()
        assert s.verify(signed_data, result.signature, None) is True

    def test_tampered_payload(self, key_dir, monkeypatch):
        s = _signer(key_dir, monkeypatch)
        result = s.sign(b"payload")
        assert s.verify(b"other|" + str(result.timestamp).encode(),
                        result.signature, result.public_key) is False

    def test_empty_signature(self, key_dir, monkeypatch):
        s = _signer(key_dir, monkeypatch)
        assert s.verify(b"payload", b"", None) is False

    def test_none_scheme_sign(self, key_dir, monkeypatch):
        s = _signer(key_dir, monkeypatch)
        s._scheme = SignatureScheme.NONE
        result = s.sign(b"payload")
        assert result.scheme is SignatureScheme.NONE
        assert result.signature == b""
        assert s.verify(b"payload", b"sig", None) is False

    def test_wrong_public_key(self, key_dir, monkeypatch):
        if not _HAS_CRYPTOGRAPHY:
            pytest.skip("cryptography unavailable")
        s = _signer(key_dir, monkeypatch)
        result = s.sign(b"payload")
        signed_data = b"payload|" + str(result.timestamp).encode()
        assert s.verify(signed_data, result.signature, b"\x00" * 32) is False

    def test_hmac_wrong_key(self, key_dir, monkeypatch):
        monkeypatch.setattr(mod, "_HAS_CRYPTOGRAPHY", False)
        s1 = _signer(key_dir, monkeypatch)
        result = s1.sign(b"payload")
        s1._hmac_key = b"different-key-material-32bytes!!!!"
        signed_data = b"payload|" + str(result.timestamp).encode()
        assert s1.verify(signed_data, result.signature, None) is False


class TestKeyPersistence:
    def test_key_reloaded(self, key_dir, monkeypatch):
        monkeypatch.delenv("AIZEE_AUDIT_SIGN_KEY", raising=False)
        kp = key_dir / "k.pem"
        s1 = AuditSigner(key_path=kp)
        s2 = AuditSigner(key_path=kp)
        assert s1.scheme() == s2.scheme()
        if _HAS_CRYPTOGRAPHY:
            assert s1.export_public_key() == s2.export_public_key()
        else:
            assert s1._hmac_key == s2._hmac_key

    def test_corrupt_ed25519_key_regenerates(self, key_dir, monkeypatch):
        if not _HAS_CRYPTOGRAPHY:
            pytest.skip("cryptography unavailable")
        monkeypatch.delenv("AIZEE_AUDIT_SIGN_KEY", raising=False)
        kp = key_dir / "k.pem"
        kp.write_bytes(b"not a pem")
        s = AuditSigner(key_path=kp)
        assert s.scheme() is SignatureScheme.ED25519  # regenerated

    def test_short_hmac_key_regenerates(self, key_dir, monkeypatch):
        monkeypatch.setattr(mod, "_HAS_CRYPTOGRAPHY", False)
        monkeypatch.delenv("AIZEE_AUDIT_SIGN_KEY", raising=False)
        kp = key_dir / "k.key"
        kp.write_bytes(b"tiny")
        s = AuditSigner(key_path=kp)
        assert s.scheme() is SignatureScheme.HMAC_SHA512
        assert len(s._hmac_key) == 64  # regenerated

    def test_export_public_key(self, key_dir, monkeypatch):
        s = _signer(key_dir, monkeypatch)
        pub = s.export_public_key()
        if _HAS_CRYPTOGRAPHY:
            assert pub is not None and len(pub) == 32
        else:
            assert pub is None

    def test_export_none_when_no_pubkey(self, key_dir, monkeypatch):
        s = _signer(key_dir, monkeypatch)
        s._ed25519_public = None
        if _HAS_CRYPTOGRAPHY:
            s._scheme = SignatureScheme.ED25519
            assert s.export_public_key() is None


class TestFilePermissions:
    def test_restrict_called_on_windows(self, key_dir, monkeypatch):
        if not _HAS_CRYPTOGRAPHY:
            pytest.skip("cryptography unavailable")
        monkeypatch.delenv("AIZEE_AUDIT_SIGN_KEY", raising=False)
        kp = key_dir / "k.pem"
        with mock.patch("runtime.audit_signing.platform.system", return_value="Windows"), \
             mock.patch("subprocess.run") as run:
            AuditSigner(key_path=kp)
            if run.called:
                args = run.call_args[0][0]
                assert args[0] == "icacls"

    def test_restrict_fallback(self, key_dir, monkeypatch):
        from runtime.audit_signing import _restrict_file_permissions
        kp = key_dir / "f.txt"
        kp.write_text("x")
        with mock.patch("runtime.audit_signing.platform.system", return_value="Windows"), \
             mock.patch("subprocess.run", side_effect=OSError("fail")):
            _restrict_file_permissions(kp)  # falls back to chmod, no raise
