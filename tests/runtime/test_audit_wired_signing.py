"""Tests for wired audit signing (P1.2): AuditSigner -> AuditLogger -> verify_chain."""

from __future__ import annotations

import json
from pathlib import Path

from runtime.audit import AuditLogger
from runtime.audit_signing import AuditSigner, SignatureResult, SignatureScheme


def _signed_logger(root: Path) -> AuditLogger:
    return AuditLogger(root, signer=AuditSigner(key_path=root / "sign.pem"))


class _FakeSigner:
    """HMAC-sha512-scheme signer stub; no public key (symmetric)."""

    def __init__(self, verify_ok: bool = True) -> None:
        self.verify_ok = verify_ok
        self.scheme_obj = SignatureScheme.HMAC_SHA512

    def sign(self, payload: bytes) -> SignatureResult:
        return SignatureResult(self.scheme_obj, b"s" * 64, None, 1.5)

    def verify(self, payload: bytes, signature: bytes, public_key: bytes | None) -> bool:
        return self.verify_ok


class _RaisingSigner:
    def sign(self, payload: bytes) -> SignatureResult:
        raise RuntimeError("sign boom")


class _EmptySigner:
    def sign(self, payload: bytes) -> SignatureResult:
        return SignatureResult(SignatureScheme.NONE, b"", None, 1.5)


def _entries(log: AuditLogger) -> list[dict]:
    return [json.loads(line) for line in log.log_file.read_text(encoding="utf-8").splitlines() if line.strip()]


class TestSignedEntries:
    def test_entries_signed_and_verify(self, tmp_path: Path) -> None:
        log = _signed_logger(tmp_path)
        log.log("evt.a", {"x": 1})
        log.log("evt.b", {"y": 2})
        entries = _entries(log)
        assert all(e.get("sig") and e.get("sig_alg") == "ed25519" and e.get("sig_pub") for e in entries)
        res = AuditLogger(tmp_path).verify_chain()
        assert res["valid"]
        assert res["signatures_checked"] == 2 and res["unsigned_entries"] == 0

    def test_verify_needs_no_private_key(self, tmp_path: Path) -> None:
        _signed_logger(tmp_path).log("evt", {"a": 1})
        res = AuditLogger(tmp_path).verify_chain()
        assert res["valid"] and res["signatures_checked"] == 1

    def test_tampered_signature_invalid(self, tmp_path: Path) -> None:
        log = _signed_logger(tmp_path)
        log.log("evt", {"a": 1})
        entry = _entries(log)[0]
        entry["sig"] = "00" * 64
        log.log_file.write_text(json.dumps(entry) + "\n", encoding="utf-8")
        res = AuditLogger(tmp_path).verify_chain()
        assert not res["valid"]
        assert res["broken_at"] is None and res["signatures_failed"] == 1

    def test_unsigned_entries_counted_not_failed(self, tmp_path: Path) -> None:
        AuditLogger(tmp_path).log("evt", {"a": 1})
        res = AuditLogger(tmp_path).verify_chain()
        assert res["valid"] and res["unsigned_entries"] == 1 and res["signatures_checked"] == 0

    def test_signer_exception_leaves_unsigned_entry(self, tmp_path: Path) -> None:
        log = AuditLogger(tmp_path, signer=_RaisingSigner())
        log.log("evt", {"a": 1})
        entry = _entries(log)[0]
        assert "sig" not in entry and entry["hash"]

    def test_empty_signature_leaves_unsigned_entry(self, tmp_path: Path) -> None:
        log = AuditLogger(tmp_path, signer=_EmptySigner())
        log.log("evt", {"a": 1})
        assert "sig" not in _entries(log)[0]


class TestSignatureSchemes:
    def test_hmac_scheme_verifies_with_signer(self, tmp_path: Path) -> None:
        AuditLogger(tmp_path, signer=_FakeSigner()).log("evt", {})
        res = AuditLogger(tmp_path, signer=_FakeSigner()).verify_chain()
        assert res["valid"] and res["signatures_checked"] == 1

    def test_hmac_scheme_unchecked_without_signer(self, tmp_path: Path) -> None:
        AuditLogger(tmp_path, signer=_FakeSigner()).log("evt", {})
        res = AuditLogger(tmp_path).verify_chain()
        assert res["valid"] and res["signatures_unchecked"] == 1

    def test_hmac_scheme_fails_on_bad_verify(self, tmp_path: Path) -> None:
        AuditLogger(tmp_path, signer=_FakeSigner()).log("evt", {})
        res = AuditLogger(tmp_path, signer=_FakeSigner(verify_ok=False)).verify_chain()
        assert not res["valid"] and res["signatures_failed"] == 1

    def test_unknown_scheme_unchecked(self, tmp_path: Path) -> None:
        log = _signed_logger(tmp_path)
        log.log("evt", {})
        entry = _entries(log)[0]
        entry["sig_alg"] = "unknown-scheme"
        log.log_file.write_text(json.dumps(entry) + "\n", encoding="utf-8")
        res = AuditLogger(tmp_path).verify_chain()
        assert res["signatures_unchecked"] == 1

    def test_malformed_sig_hex_fails(self, tmp_path: Path) -> None:
        log = _signed_logger(tmp_path)
        log.log("evt", {})
        entry = _entries(log)[0]
        entry["sig"] = "zz-not-hex"
        log.log_file.write_text(json.dumps(entry) + "\n", encoding="utf-8")
        res = AuditLogger(tmp_path).verify_chain()
        assert res["signatures_failed"] == 1


class TestLegacyPrefix:
    """Entries written before hash-chaining shipped have no prev_hash/hash.

    A leading run of them is a legacy prefix — counted and reported as
    unverifiable, not a break. An unchained entry *after* the chain starts
    is a hole and must break verification.
    """

    @staticmethod
    def _legacy(ts: str) -> str:
        return json.dumps({"ts": ts, "type": "action.allowed", "details": {"action": "Read"}})

    def test_legacy_prefix_then_chained_is_valid(self, tmp_path: Path) -> None:
        log_file = tmp_path / "state" / "audit.log"
        log_file.parent.mkdir(parents=True)
        log_file.write_text(self._legacy("2026-07-14T00:00:00+00:00") + "\n", encoding="utf-8")
        log = AuditLogger(tmp_path)
        log.log("evt", {"a": 1})
        res = log.verify_chain()
        assert res["valid"] and res["entries_checked"] == 1
        assert res["legacy_entries"] == 1 and res["broken_at"] is None

    def test_unchained_hole_after_chain_start_breaks(self, tmp_path: Path) -> None:
        log = AuditLogger(tmp_path)
        log.log("evt.a", {"a": 1})
        with log.log_file.open("a", encoding="utf-8") as f:
            f.write(self._legacy("2026-10-08T00:00:00+00:00") + "\n")
        res = log.verify_chain()
        assert not res["valid"] and res["broken_at"] == 1

    def test_all_legacy_file_is_valid_with_count(self, tmp_path: Path) -> None:
        log_file = tmp_path / "state" / "audit.log"
        log_file.parent.mkdir(parents=True)
        log_file.write_text(
            self._legacy("2026-07-14T00:00:00+00:00") + "\n"
            + self._legacy("2026-07-15T00:00:00+00:00") + "\n",
            encoding="utf-8",
        )
        res = AuditLogger(tmp_path).verify_chain()
        assert res["valid"] and res["entries_checked"] == 0 and res["legacy_entries"] == 2

    def test_partial_chain_fields_count_as_legacy(self, tmp_path: Path) -> None:
        log_file = tmp_path / "state" / "audit.log"
        log_file.parent.mkdir(parents=True)
        # prev_hash present but hash missing — pre-chain partial format.
        log_file.write_text(
            json.dumps({"ts": "t", "type": "x", "details": {}, "prev_hash": "0" * 64}) + "\n",
            encoding="utf-8",
        )
        res = AuditLogger(tmp_path).verify_chain()
        assert res["valid"] and res["legacy_entries"] == 1
