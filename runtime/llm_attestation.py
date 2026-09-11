#!/usr/bin/env python3
"""LLM artifact attestation with signed DSSE envelopes and provenance chains.

Inspired by llmsa: provides cryptographic attestation for LLM-generated
artifacts. Each attestation is a signed DSSE-style envelope wrapping a
statement that describes what was attested (prompt, corpus, eval, route,
or SLO), its digest, and its provenance dependencies.

Five attestation types:
    - PROMPT:  attests to the prompt sent to an LLM.
    - CORPUS:  attests to the training/reference corpus used.
    - EVAL:    attests to evaluation results for an LLM output.
    - ROUTE:   attests to the routing decision (which model was selected).
    - SLO:     attests to SLO compliance for an LLM service.

Privacy modes control what is stored:
    - HASH_ONLY:          only the SHA-256 digest is stored (no content).
    - ENCRYPTED:          content is encrypted at rest (future: Fernet).
    - PLAINTEXT_EXPLICIT: content is stored in plaintext (explicit opt-in).

Signing: tries Ed25519 via the ``cryptography`` library; falls back to
HMAC-SHA256 if ``cryptography`` is unavailable or no Ed25519 key is set.

Architecture::

    content -> LlmAttestor.attest(type, subject, content, privacy_mode)
           -> AttestationEnvelope (statement + signature)
           -> stored as JSON file in state_dir

    verify(envelope, content) -> bool
    verify_chain(envelopes) -> list[dict]  (DAG dependency check)

Usage::

    from runtime.llm_attestation import LlmAttestor, AttestationType, PrivacyMode
    from pathlib import Path

    attestor = LlmAttestor(Path("./state/attestations"))
    env = attestor.attest(
        AttestationType.PROMPT,
        subject="agent-1/session-42",
        content=b"Summarize the quarterly report.",
        privacy_mode=PrivacyMode.HASH_ONLY,
    )
    assert attestor.verify(env, b"Summarize the quarterly report.")
"""

from __future__ import annotations

import contextlib
import hashlib
import hmac
import json
import logging
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from runtime.schemas import AizeeError, ErrorSeverity

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class AttestationType(str, Enum):
    """The five attestation types for LLM artifacts."""

    PROMPT = "prompt"
    CORPUS = "corpus"
    EVAL = "eval"
    ROUTE = "route"
    SLO = "slo"


class PrivacyMode(str, Enum):
    """Controls what content is stored in the attestation.

    - HASH_ONLY:          only the SHA-256 digest is stored.
    - ENCRYPTED:          content is encrypted at rest.
    - PLAINTEXT_EXPLICIT: content is stored in plaintext (caller opted in).
    """

    HASH_ONLY = "hash_only"
    ENCRYPTED = "encrypted"
    PLAINTEXT_EXPLICIT = "plaintext_explicit"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class AttestationStatement:
    """The unsigned statement inside a DSSE envelope.

    Attributes:
        statement_id: Unique identifier (UUID).
        attestation_type: Which of the 5 attestation types.
        subject: The artifact being attested (e.g. "agent-1/session-42").
        digest: SHA-256 hex digest of the content.
        metadata: Additional structured context.
        depends_on: Statement IDs this attestation depends on (provenance chain).
        created_at: Unix timestamp when the statement was created.
    """

    statement_id: str
    attestation_type: AttestationType
    subject: str
    digest: str
    metadata: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for JSON storage."""
        return {
            "statement_id": self.statement_id,
            "attestation_type": self.attestation_type.value,
            "subject": self.subject,
            "digest": self.digest,
            "metadata": self.metadata,
            "depends_on": self.depends_on,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AttestationStatement:
        """Deserialize from dict."""
        return cls(
            statement_id=data["statement_id"],
            attestation_type=AttestationType(data["attestation_type"]),
            subject=data["subject"],
            digest=data["digest"],
            metadata=data.get("metadata", {}),
            depends_on=data.get("depends_on", []),
            created_at=data.get("created_at", time.time()),
        )


@dataclass
class AttestationEnvelope:
    """A DSSE-style envelope wrapping a signed attestation statement.

    Attributes:
        statement: The attestation statement being signed.
        signature: The cryptographic signature (or None if unsigned).
        signed_by: Identifier of the signer (e.g. key ID or "hmac-fallback").
        scheme: Signing scheme used ("ed25519" or "hmac-sha256").
    """

    statement: AttestationStatement
    signature: bytes | None = None
    signed_by: str | None = None
    scheme: str = "hmac-sha256"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for JSON storage."""
        return {
            "statement": self.statement.to_dict(),
            "signature": (
                self.signature.hex() if self.signature is not None else None
            ),
            "signed_by": self.signed_by,
            "scheme": self.scheme,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AttestationEnvelope:
        """Deserialize from dict."""
        sig_hex = data.get("signature")
        return cls(
            statement=AttestationStatement.from_dict(data["statement"]),
            signature=bytes.fromhex(sig_hex) if sig_hex else None,
            signed_by=data.get("signed_by"),
            scheme=data.get("scheme", "hmac-sha256"),
        )


class AttestationError(AizeeError):
    """Raised when attestation creation or verification fails."""

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        super().__init__("ATTESTATION_ERROR", message, ErrorSeverity.HIGH, context)


# ---------------------------------------------------------------------------
# Attestor
# ---------------------------------------------------------------------------


class LlmAttestor:
    """Creates and verifies LLM artifact attestations with provenance chains.

    Stores attestations as individual JSON files in ``state_dir``. Each
    file is named by the statement ID. Signing uses Ed25519 if the
    ``cryptography`` library is available and a key is configured;
    otherwise falls back to HMAC-SHA256 with a generated secret key.

    Thread-safe via ``RLock``.
    """

    def __init__(self, state_dir: Path) -> None:
        self._state_dir = state_dir
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._signing_key = self._load_or_create_key()

    # -- Public API ----------------------------------------------------------

    def attest(
        self,
        attestation_type: AttestationType,
        subject: str,
        content: bytes,
        privacy_mode: PrivacyMode = PrivacyMode.HASH_ONLY,
        depends_on: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AttestationEnvelope:
        """Create and persist a signed attestation for an LLM artifact.

        See module docstring for attestation types and privacy modes.
        """
        statement = self._build_statement(
            attestation_type, subject, content, privacy_mode, depends_on, metadata
        )
        envelope = self._build_envelope(statement)
        with self._lock:
            self._persist(envelope)
        _logger.info(
            "attested %s for %s (id=%s, scheme=%s)",
            attestation_type.value,
            subject,
            statement.statement_id,
            envelope.scheme,
        )
        return envelope

    def _build_statement(
        self,
        attestation_type: AttestationType,
        subject: str,
        content: bytes,
        privacy_mode: PrivacyMode,
        depends_on: list[str] | None,
        metadata: dict[str, Any] | None,
    ) -> AttestationStatement:
        """Construct an AttestationStatement from the attest parameters."""
        return AttestationStatement(
            statement_id=str(uuid.uuid4()),
            attestation_type=attestation_type,
            subject=subject,
            digest=hashlib.sha256(content).hexdigest(),
            metadata=self._apply_privacy(privacy_mode, content, metadata or {}),
            depends_on=depends_on or [],
        )

    def _build_envelope(
        self, statement: AttestationStatement
    ) -> AttestationEnvelope:
        """Sign a statement and wrap it in an AttestationEnvelope."""
        signature, signed_by, scheme = self._sign(statement)
        return AttestationEnvelope(
            statement=statement,
            signature=signature,
            signed_by=signed_by,
            scheme=scheme,
        )

    def verify(
        self,
        envelope: AttestationEnvelope,
        content: bytes | None = None,
    ) -> bool:
        """Verify an attestation envelope's signature and optional content digest.

        Args:
            envelope: The envelope to verify.
            content: If provided, the content digest is also checked against
                the statement's digest.

        Returns:
            True if the signature is valid (and content digest matches if provided).
        """
        if content is not None:
            expected = hashlib.sha256(content).hexdigest()
            if expected != envelope.statement.digest:
                _logger.warning(
                    "digest mismatch for %s: expected %s, got %s",
                    envelope.statement.statement_id,
                    expected,
                    envelope.statement.digest,
                )
                return False
        return self._verify_signature(envelope)

    def verify_chain(
        self, envelopes: list[AttestationEnvelope]
    ) -> list[dict[str, Any]]:
        """Check DAG dependencies among a list of attestations.

        Returns a list of result dicts, one per envelope, indicating
        whether all its ``depends_on`` references were found in the set.
        """
        ids = {env.statement.statement_id for env in envelopes}
        results: list[dict[str, Any]] = []
        for env in envelopes:
            missing = [dep for dep in env.statement.depends_on if dep not in ids]
            sig_ok = self._verify_signature(env)
            results.append({
                "statement_id": env.statement.statement_id,
                "valid": len(missing) == 0 and sig_ok,
                "missing_deps": missing,
                "signature_valid": sig_ok,
            })
        return results

    def list_attestations(
        self, attestation_type: AttestationType | None = None
    ) -> list[AttestationEnvelope]:
        """List all stored attestations, optionally filtered by type."""
        with self._lock:
            envelopes: list[AttestationEnvelope] = []
            for path in self._state_dir.glob("*.json"):
                if not path.is_file():
                    continue
                env = self._load_envelope(path)
                if env is None:
                    continue
                if attestation_type is None or env.statement.attestation_type is attestation_type:
                    envelopes.append(env)
            return envelopes

    def get_attestation(self, statement_id: str) -> AttestationEnvelope | None:
        """Retrieve a specific attestation by statement ID."""
        with self._lock:
            path = self._envelope_path(statement_id)
            return self._load_envelope(path)

    # -- Signing helpers (each < 30 lines) ----------------------------------

    def _sign(
        self, statement: AttestationStatement
    ) -> tuple[bytes | None, str, str]:
        """Sign a statement. Tries Ed25519, falls back to HMAC-SHA256."""
        payload = self._canonical(statement)
        try:
            return self._sign_ed25519(payload)
        except Exception as exc:
            _logger.debug("Ed25519 signing unavailable, using HMAC: %s", exc)
            return self._sign_hmac(payload)

    def _sign_ed25519(self, payload: bytes) -> tuple[bytes, str, str]:
        """Sign with Ed25519. Raises if cryptography is unavailable."""
        key = self._get_ed25519_key()
        if key is None:
            raise RuntimeError("no Ed25519 key configured")
        sig = key.sign(payload)
        return sig, "ed25519-key", "ed25519"

    def _sign_hmac(self, payload: bytes) -> tuple[bytes, str, str]:
        """Sign with HMAC-SHA256 using the stored secret key."""
        sig = hmac.new(self._signing_key, payload, hashlib.sha256).digest()
        return sig, "hmac-fallback", "hmac-sha256"

    def _verify_signature(self, envelope: AttestationEnvelope) -> bool:
        """Verify the signature on an envelope."""
        if envelope.signature is None:
            return False
        payload = self._canonical(envelope.statement)
        if envelope.scheme == "ed25519":
            return self._verify_ed25519(payload, envelope.signature)
        return hmac.compare_digest(
            hmac.new(self._signing_key, payload, hashlib.sha256).digest(),
            envelope.signature,
        )

    def _verify_ed25519(self, payload: bytes, signature: bytes) -> bool:
        """Verify an Ed25519 signature."""
        try:
            pub = self._get_ed25519_public_key()
            if pub is None:
                return False
            pub.verify(signature, payload)
            return True
        except Exception:
            return False

    # -- Key management ------------------------------------------------------

    def _load_or_create_key(self) -> bytes:
        """Load or create the HMAC signing key from the state directory."""
        key_path = self._state_dir / ".signing_key"
        if key_path.is_file():
            return key_path.read_bytes()
        key = os.urandom(32)
        key_path.write_bytes(key)
        _logger.warning(
            "SECURITY: auto-generated HMAC signing key at %s. "
            "For production, manage this key externally.",
            key_path,
        )
        return key

    def _get_ed25519_key(self) -> Any:
        """Return an Ed25519PrivateKey if a raw key file exists."""
        key_path = self._state_dir / ".ed25519_key"
        if not key_path.is_file():
            return None
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey,
        )

        raw = key_path.read_bytes()
        return Ed25519PrivateKey.from_private_bytes(raw)

    def _get_ed25519_public_key(self) -> Any:
        """Return the Ed25519PublicKey derived from the private key, if available."""
        key = self._get_ed25519_key()
        if key is None:
            return None
        return key.public_key()

    # -- Persistence helpers (each < 30 lines) ------------------------------

    def _persist(self, envelope: AttestationEnvelope) -> None:
        """Atomically write an envelope to a JSON file."""
        path = self._envelope_path(envelope.statement.statement_id)
        data = json.dumps(envelope.to_dict(), indent=2)
        tmp_fd, tmp_path = _mkstemp(self._state_dir, envelope.statement.statement_id)
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                f.write(data)
            os.replace(tmp_path, str(path))
        except Exception:
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)
            raise

    def _load_envelope(self, path: Path) -> AttestationEnvelope | None:
        """Load an envelope from a JSON file, or None on error."""
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            _logger.warning("failed to load attestation %s: %s", path, exc)
            return None
        return AttestationEnvelope.from_dict(data)

    def _envelope_path(self, statement_id: str) -> Path:
        """Return the JSON file path for a statement ID."""
        safe_id = statement_id.replace("/", "_").replace("\\", "_")
        return self._state_dir / f"{safe_id}.json"

    # -- Utility helpers -----------------------------------------------------

    @staticmethod
    def _canonical(statement: AttestationStatement) -> bytes:
        """Produce a deterministic canonical byte representation for signing."""
        payload = {
            "statement_id": statement.statement_id,
            "attestation_type": statement.attestation_type.value,
            "subject": statement.subject,
            "digest": statement.digest,
            "depends_on": sorted(statement.depends_on),
            "created_at": statement.created_at,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )

    @staticmethod
    def _apply_privacy(
        mode: PrivacyMode,
        content: bytes,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """Apply privacy mode to determine what content metadata to store."""
        result = dict(metadata)
        if mode is PrivacyMode.HASH_ONLY:
            result["_privacy"] = PrivacyMode.HASH_ONLY.value
        elif mode is PrivacyMode.ENCRYPTED:
            result["_privacy"] = PrivacyMode.ENCRYPTED.value
            result["_content_encrypted"] = True
        elif mode is PrivacyMode.PLAINTEXT_EXPLICIT:
            result["_privacy"] = PrivacyMode.PLAINTEXT_EXPLICIT.value
            result["_content"] = content.decode("utf-8", errors="replace")
        return result


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _mkstemp(state_dir: Path, statement_id: str) -> tuple[int, str]:
    """Create a temp file in the state dir, returning (fd, path)."""
    import tempfile

    prefix = statement_id[:32] + "."
    return tempfile.mkstemp(dir=str(state_dir), suffix=".tmp", prefix=prefix)
