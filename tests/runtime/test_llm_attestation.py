"""Tests for runtime/llm_attestation.py — signed DSSE attestations."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from runtime.llm_attestation import (
    AttestationEnvelope,
    AttestationError,
    AttestationStatement,
    AttestationType,
    LlmAttestor,
    PrivacyMode,
)


@pytest.fixture()
def state_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture()
def attestor(state_dir):
    return LlmAttestor(state_dir)


class TestAttest:
    def test_creates_envelope(self, attestor):
        env = attestor.attest(AttestationType.PROMPT, "agent-1/s1", b"hello")
        assert env.statement.attestation_type is AttestationType.PROMPT
        assert env.statement.subject == "agent-1/s1"
        assert env.signature is not None
        assert env.scheme in ("hmac-sha256", "ed25519")

    def test_persisted(self, attestor, state_dir):
        env = attestor.attest(AttestationType.EVAL, "s", b"data")
        files = list(state_dir.glob("*.json"))
        assert len(files) == 1
        data = json.loads(files[0].read_text())
        assert data["statement"]["statement_id"] == env.statement.statement_id

    def test_digest_computed(self, attestor):
        import hashlib
        env = attestor.attest(AttestationType.CORPUS, "s", b"content")
        assert env.statement.digest == hashlib.sha256(b"content").hexdigest()

    def test_depends_on(self, attestor):
        e1 = attestor.attest(AttestationType.PROMPT, "s", b"a")
        e2 = attestor.attest(AttestationType.EVAL, "s", b"b",
                             depends_on=[e1.statement.statement_id])
        assert e2.statement.depends_on == [e1.statement.statement_id]

    def test_metadata(self, attestor):
        env = attestor.attest(AttestationType.ROUTE, "s", b"x",
                             metadata={"model": "gpt-4o"})
        assert env.statement.metadata["model"] == "gpt-4o"


class TestPrivacyModes:
    def test_hash_only(self, attestor):
        env = attestor.attest(AttestationType.PROMPT, "s", b"secret",
                             privacy_mode=PrivacyMode.HASH_ONLY)
        assert env.statement.metadata["_privacy"] == "hash_only"
        assert "secret" not in json.dumps(env.statement.metadata)

    def test_encrypted_flag(self, attestor):
        env = attestor.attest(AttestationType.PROMPT, "s", b"data",
                             privacy_mode=PrivacyMode.ENCRYPTED)
        assert env.statement.metadata["_privacy"] == "encrypted"
        assert env.statement.metadata["_content_encrypted"] is True

    def test_plaintext_explicit(self, attestor):
        env = attestor.attest(AttestationType.PROMPT, "s", b"visible",
                             privacy_mode=PrivacyMode.PLAINTEXT_EXPLICIT)
        assert env.statement.metadata["_privacy"] == "plaintext_explicit"
        assert env.statement.metadata["_content"] == "visible"


class TestVerify:
    def test_verify_no_content(self, attestor):
        env = attestor.attest(AttestationType.SLO, "s", b"data")
        assert attestor.verify(env) is True

    def test_verify_correct_content(self, attestor):
        env = attestor.attest(AttestationType.PROMPT, "s", b"content")
        assert attestor.verify(env, b"content") is True

    def test_verify_wrong_content(self, attestor):
        env = attestor.attest(AttestationType.PROMPT, "s", b"content")
        assert attestor.verify(env, b"tampered") is False

    def test_verify_tampered_signature(self, attestor):
        env = attestor.attest(AttestationType.PROMPT, "s", b"data")
        env.signature = b"\x00" * 32
        assert attestor.verify(env) is False

    def test_verify_no_signature(self, attestor):
        env = attestor.attest(AttestationType.PROMPT, "s", b"data")
        env.signature = None
        assert attestor.verify(env) is False

    def test_verify_tampered_statement(self, attestor):
        env = attestor.attest(AttestationType.PROMPT, "s", b"data")
        env.statement.subject = "attacker"
        assert attestor.verify(env) is False

    def test_different_attestor_key_fails(self, attestor):
        env = attestor.attest(AttestationType.PROMPT, "s", b"data")
        with tempfile.TemporaryDirectory() as d2:
            other = LlmAttestor(Path(d2))  # different HMAC key
            if env.scheme == "hmac-sha256":
                assert other.verify(env) is False


class TestVerifyChain:
    def test_valid_chain(self, attestor):
        e1 = attestor.attest(AttestationType.PROMPT, "s", b"a")
        e2 = attestor.attest(AttestationType.EVAL, "s", b"b",
                             depends_on=[e1.statement.statement_id])
        results = attestor.verify_chain([e1, e2])
        assert all(r["valid"] for r in results)

    def test_missing_dep(self, attestor):
        e2 = attestor.attest(AttestationType.EVAL, "s", b"b",
                             depends_on=["nonexistent-id"])
        results = attestor.verify_chain([e2])
        assert results[0]["valid"] is False
        assert results[0]["missing_deps"] == ["nonexistent-id"]

    def test_bad_sig_in_chain(self, attestor):
        e1 = attestor.attest(AttestationType.PROMPT, "s", b"a")
        e1.signature = b"\x00" * 64
        results = attestor.verify_chain([e1])
        assert results[0]["signature_valid"] is False
        assert results[0]["valid"] is False

    def test_empty_chain(self, attestor):
        assert attestor.verify_chain([]) == []


class TestPersistence:
    def test_list_attestations(self, attestor):
        attestor.attest(AttestationType.PROMPT, "s", b"a")
        attestor.attest(AttestationType.EVAL, "s", b"b")
        assert len(attestor.list_attestations()) == 2
        assert len(attestor.list_attestations(AttestationType.PROMPT)) == 1

    def test_get_attestation(self, attestor):
        env = attestor.attest(AttestationType.ROUTE, "s", b"x")
        got = attestor.get_attestation(env.statement.statement_id)
        assert got is not None
        assert got.statement.subject == "s"

    def test_get_missing(self, attestor):
        assert attestor.get_attestation("nope") is None

    def test_corrupt_file_skipped(self, attestor, state_dir):
        attestor.attest(AttestationType.PROMPT, "s", b"ok")
        (state_dir / "corrupt.json").write_text("{bad")
        assert len(attestor.list_attestations()) == 1

    def test_roundtrip_preserves_signature(self, attestor):
        env = attestor.attest(AttestationType.SLO, "s", b"d")
        loaded = attestor.get_attestation(env.statement.statement_id)
        assert loaded.signature == env.signature
        assert attestor.verify(loaded, b"d") is True


class TestKeyManagement:
    def test_signing_key_persisted(self, state_dir):
        a1 = LlmAttestor(state_dir)
        a2 = LlmAttestor(state_dir)
        assert a1._signing_key == a2._signing_key

    def test_ed25519_path(self, state_dir):
        """If cryptography is available, Ed25519 keys produce ed25519 sigs."""
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import (
                Ed25519PrivateKey,
            )
            from cryptography.hazmat.primitives.serialization import (
                Encoding,
                NoEncryption,
                PrivateFormat,
            )
        except ImportError:
            pytest.skip("cryptography unavailable")
        key = Ed25519PrivateKey.generate()
        raw = key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
        (state_dir / ".ed25519_key").write_bytes(raw)
        att = LlmAttestor(state_dir)
        env = att.attest(AttestationType.PROMPT, "s", b"data")
        assert env.scheme == "ed25519"
        assert att.verify(env, b"data") is True
        # tampered
        env.statement.subject = "evil"
        assert att.verify(env) is False


class TestSerialization:
    def test_statement_roundtrip(self):
        s = AttestationStatement("id1", AttestationType.EVAL, "subj", "dg",
                                 {"k": 1}, ["dep1"], 123.0)
        s2 = AttestationStatement.from_dict(s.to_dict())
        assert s2.statement_id == "id1"
        assert s2.attestation_type is AttestationType.EVAL
        assert s2.depends_on == ["dep1"]

    def test_envelope_roundtrip(self):
        s = AttestationStatement("id", AttestationType.PROMPT, "s", "d")
        env = AttestationEnvelope(s, b"\x01\x02", "hmac-fallback", "hmac-sha256")
        env2 = AttestationEnvelope.from_dict(json.loads(json.dumps(env.to_dict())))
        assert env2.signature == b"\x01\x02"
        assert env2.scheme == "hmac-sha256"

    def test_envelope_no_sig_roundtrip(self):
        s = AttestationStatement("id", AttestationType.PROMPT, "s", "d")
        env = AttestationEnvelope(s, None, None)
        env2 = AttestationEnvelope.from_dict(env.to_dict())
        assert env2.signature is None

    def test_attestation_error(self):
        err = AttestationError("x", {"a": 1})
        assert err.error_code == "ATTESTATION_ERROR"
