"""Gap tests for runtime/audit_signing.py — key paths, OSError, NONE scheme."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import runtime.audit_signing as m
from runtime.audit_signing import AuditSigner, SignatureScheme, _restrict_file_permissions


class TestRestrictPermissions:
    def test_posix_chmod(self, tmp_path):
        f = tmp_path / "k.pem"
        f.write_bytes(b"key")
        with patch("runtime.audit_signing.platform.system", return_value="Linux"):
            _restrict_file_permissions(f)

    def test_windows_getlogin_fallback(self, tmp_path):
        f = tmp_path / "k.pem"
        f.write_bytes(b"key")
        with (
            patch("runtime.audit_signing.platform.system", return_value="Windows"),
            patch("os.getlogin", side_effect=OSError("no login")),
            patch("subprocess.run") as run,
        ):
            _restrict_file_permissions(f)
            assert run.called

    def test_all_fail_suppressed(self, tmp_path):
        f = tmp_path / "k.pem"
        f.write_bytes(b"key")
        with (
            patch("runtime.audit_signing.platform.system", side_effect=RuntimeError("boom")),
            patch.object(Path, "chmod", side_effect=OSError("nope")),
        ):
            _restrict_file_permissions(f)  # must not raise


class TestKeyPathResolution:
    def test_env_path_wins(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AIZEE_AUDIT_SIGN_KEY", str(tmp_path / "env.key"))
        s = AuditSigner(tmp_path / "ignored.key")
        assert s._resolve_key_path("x") == tmp_path / "env.key"

    def test_default_root_path(self, monkeypatch, tmp_path):
        monkeypatch.delenv("AIZEE_AUDIT_SIGN_KEY", raising=False)
        monkeypatch.setenv("AIZEE_ROOT", str(tmp_path))
        s = AuditSigner.__new__(AuditSigner)
        s._key_path = None
        s._scheme = SignatureScheme.NONE
        s._ed25519_private = None
        s._ed25519_public = None
        s._hmac_key = None
        out = s._resolve_key_path("pem")
        assert out == tmp_path / "state" / "audit_sign.pem"


class TestHmacPath:
    def test_hmac_init_and_roundtrip(self, tmp_path, monkeypatch):
        monkeypatch.setattr(m, "_HAS_CRYPTOGRAPHY", False)
        s = AuditSigner(tmp_path / "hmac.key")
        assert s.scheme() is SignatureScheme.HMAC_SHA512
        res = s.sign(b"payload")
        assert res.scheme is SignatureScheme.HMAC_SHA512
        assert res.signature

    def test_hmac_loads_existing_key(self, tmp_path, monkeypatch):
        monkeypatch.setattr(m, "_HAS_CRYPTOGRAPHY", False)
        kf = tmp_path / "hmac.key"
        kf.write_bytes(b"k" * 40)
        s = AuditSigner(kf)
        assert s._hmac_key == b"k" * 40

    def test_hmac_short_key_regenerates(self, tmp_path, monkeypatch):
        monkeypatch.setattr(m, "_HAS_CRYPTOGRAPHY", False)
        kf = tmp_path / "hmac.key"
        kf.write_bytes(b"tiny")
        s = AuditSigner(kf)
        assert len(s._hmac_key) == 64

    def test_hmac_read_oserror_regenerates(self, tmp_path, monkeypatch):
        monkeypatch.setattr(m, "_HAS_CRYPTOGRAPHY", False)
        kf = tmp_path / "hmac.key"
        kf.write_bytes(b"k" * 40)
        orig = Path.read_bytes
        def boom(self, *a, **kw):
            if self == kf and self.stat().st_size:
                raise OSError("locked")
            return orig(self, *a, **kw)
        with patch.object(Path, "read_bytes", boom):
            s = AuditSigner(kf)
        assert len(s._hmac_key) == 64

    def test_hmac_persist_oserror(self, tmp_path, monkeypatch):
        monkeypatch.setattr(m, "_HAS_CRYPTOGRAPHY", False)
        with patch.object(Path, "write_bytes", side_effect=OSError("rofs")):
            s = AuditSigner(tmp_path / "sub" / "hmac.key")
        assert s._hmac_key is not None  # generated in memory anyway

    def test_hmac_sign_none_key(self, tmp_path, monkeypatch):
        monkeypatch.setattr(m, "_HAS_CRYPTOGRAPHY", False)
        s = AuditSigner(tmp_path / "h.key")
        s._hmac_key = None
        res = s.sign(b"x")
        assert res.scheme is SignatureScheme.NONE

    def test_hmac_verify_none_key(self, tmp_path, monkeypatch):
        monkeypatch.setattr(m, "_HAS_CRYPTOGRAPHY", False)
        s = AuditSigner(tmp_path / "h.key")
        s._hmac_key = None
        assert s.verify(b"p", b"sig", None) is False

    def test_hmac_verify_roundtrip_and_tamper(self, tmp_path, monkeypatch):
        monkeypatch.setattr(m, "_HAS_CRYPTOGRAPHY", False)
        s = AuditSigner(tmp_path / "h.key")
        # verify() expects payload WITHOUT appended ts; replicate manually
        import hashlib
        import hmac
        sig = hmac.new(s._hmac_key, b"data", hashlib.sha512).digest()
        assert s.verify(b"data", sig, None) is True
        assert s.verify(b"data", b"bad", None) is False


class TestEd25519Edges:
    def test_non_ed25519_pem_regenerates(self, tmp_path):
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pem = rsa_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        kf = tmp_path / "k.pem"
        kf.write_bytes(pem)
        s = AuditSigner(kf)
        assert s.scheme() is SignatureScheme.ED25519  # regenerated
        # the file now contains an ed25519 key
        s2 = AuditSigner(kf)
        assert s2.scheme() is SignatureScheme.ED25519

    def test_persist_oserror(self, tmp_path):
        with patch.object(Path, "write_bytes", side_effect=OSError("rofs")):
            s = AuditSigner(tmp_path / "sub" / "k.pem")
        assert s.scheme() is SignatureScheme.ED25519

    def test_sign_no_private_key(self, tmp_path):
        s = AuditSigner(tmp_path / "k.pem")
        s._ed25519_private = None
        res = s.sign(b"x")
        assert res.scheme is SignatureScheme.NONE

    def test_sign_no_public_key(self, tmp_path):
        s = AuditSigner(tmp_path / "k.pem")
        s._ed25519_public = None
        res = s.sign(b"x")
        assert res.scheme is SignatureScheme.ED25519
        assert res.public_key is None

    def test_verify_no_public_key(self, tmp_path):
        s = AuditSigner(tmp_path / "k.pem")
        assert s.verify(b"p", b"s", None) is False

    def test_verify_bad_signature(self, tmp_path):
        s = AuditSigner(tmp_path / "k.pem")
        pub = s.export_public_key()
        assert pub is not None
        assert s.verify(b"payload", b"bad-sig", pub) is False

    def test_export_public_key_none(self, tmp_path):
        s = AuditSigner(tmp_path / "k.pem")
        s._ed25519_public = None
        assert s.export_public_key() is None

    def test_verify_none_scheme(self, tmp_path, monkeypatch):
        monkeypatch.setattr(m, "_HAS_CRYPTOGRAPHY", False)
        s = AuditSigner(tmp_path / "h.key")
        s._scheme = SignatureScheme.NONE
        assert s.verify(b"p", b"s", None) is False
