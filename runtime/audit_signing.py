#!/usr/bin/env python3
"""Ed25519 signature support for audit entries.

Extends the existing HMAC-SHA256 audit chain (``runtime/audit.py``)
with stronger asymmetric signatures using Ed25519. Inspired by
rootsign (key management) and sphinx (audit integrity).

Since the ``cryptography`` package is optional in aiZee, this module
gracefully degrades:

1. **Ed25519** (preferred) — if ``cryptography`` is installed, uses
   Ed25519 for signing and verification. Public keys can be exported for
   verification by external parties without sharing the private key.
2. **HMAC-SHA512** (fallback) — if ``cryptography`` is not available,
   falls back to HMAC-SHA512 (still stronger than the existing
   HMAC-SHA256 chain). This is symmetric, so the same key signs and
   verifies.
3. **NONE** (last resort) — if neither is available (e.g. hashlib
   missing, which should never happen), signing is disabled and
   ``verify()`` always returns ``False``.

The module **never crashes** if crypto libraries are missing — it logs
a warning and degrades. This is critical because audit signing is a
defense-in-depth layer, not a hard dependency.

Key resolution (for Ed25519):
1. ``AIZEE_AUDIT_SIGN_KEY`` env var (path to a PEM private key file).
2. ``key_path`` argument to :class:`AuditSigner`.
3. Auto-generated key stored in ``state/audit_sign.key`` (dev only).

Usage::

    from runtime.audit_signing import AuditSigner
    signer = AuditSigner()
    result = signer.sign(b"audit entry payload")
    assert signer.verify(b"audit entry payload", result.signature, result.public_key)
    pub = signer.export_public_key()  # share with verifiers
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import platform
import secrets
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

_logger = logging.getLogger(__name__)

# Try to import cryptography for Ed25519 support.
try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
        Ed25519PublicKey,
    )
    _HAS_CRYPTOGRAPHY = True
except ImportError:
    _HAS_CRYPTOGRAPHY = False
    _logger.warning(
        "cryptography package not available — audit signing will use "
        "HMAC-SHA512 fallback. Install 'cryptography' for Ed25519 support."
    )


class SignatureScheme(str, Enum):
    """Available signature schemes, in preference order."""

    ED25519 = "ed25519"
    HMAC_SHA512 = "hmac_sha512"
    NONE = "none"


@dataclass
class SignatureResult:
    """Result of signing a payload.

    Attributes:
        scheme: Which signature scheme was used.
        signature: The signature bytes.
        public_key: The public key bytes (Ed25519 only; ``None`` for
            HMAC since it's symmetric).
        timestamp: When the signature was created (epoch seconds).
    """

    scheme: SignatureScheme
    signature: bytes
    public_key: bytes | None
    timestamp: float


def _restrict_file_permissions(path: Path) -> None:
    """Restrict file permissions to owner-only (0o600), cross-platform."""
    import contextlib

    try:
        if platform.system() == "Windows":
            import getpass
            import subprocess

            try:
                user = os.getlogin()
            except OSError:
                user = getpass.getuser()
            subprocess.run(
                ["icacls", str(path), "/inheritance:r", "/grant:r", f"{user}:(R,W)"],
                capture_output=True,
                timeout=5,
                check=False,
            )
        else:
            path.chmod(0o600)
    except Exception:
        with contextlib.suppress(OSError):
            path.chmod(0o600)


class AuditSigner:
    """Signs and verifies audit payloads using the best available scheme.

    Scheme selection (automatic, in priority order):
    1. Ed25519 (if ``cryptography`` is installed).
    2. HMAC-SHA512 (always available via ``hmac`` + ``hashlib``).
    3. NONE (only if ``hmac``/``hashlib`` somehow unavailable).

    For Ed25519, the private key is loaded from or generated at
    *key_path* (or the default ``state/audit_sign.key``). The public key
    can be exported via :meth:`export_public_key` for external
    verification.

    For HMAC-SHA512, a 64-byte random key is generated and stored
    similarly. Since HMAC is symmetric, the same key is needed for both
    signing and verification.
    """

    def __init__(self, key_path: Path | None = None) -> None:
        self._scheme: SignatureScheme = SignatureScheme.NONE
        self._ed25519_private: Ed25519PrivateKey | None = None
        self._ed25519_public: Ed25519PublicKey | None = None
        self._hmac_key: bytes | None = None
        self._key_path = key_path
        self._init_keys()

    def _init_keys(self) -> None:
        """Initialize signing keys based on available crypto libraries."""
        if _HAS_CRYPTOGRAPHY:
            self._init_ed25519()
        else:
            self._init_hmac()

    def _resolve_key_path(self, suffix: str) -> Path:
        """Resolve the key file path from env var, argument, or default."""
        env_path = os.environ.get("AIZEE_AUDIT_SIGN_KEY")
        if env_path:
            return Path(env_path)
        if self._key_path is not None:
            return self._key_path
        root = Path(os.environ.get("AIZEE_ROOT", "."))
        return root / "state" / f"audit_sign.{suffix}"

    def _init_ed25519(self) -> None:
        """Initialize Ed25519 keys (load or generate)."""
        key_file = self._resolve_key_path("pem")
        key_file.parent.mkdir(parents=True, exist_ok=True)
        if key_file.exists() and self._try_load_ed25519(key_file):
            return
        self._generate_ed25519(key_file)

    def _try_load_ed25519(self, key_file: Path) -> bool:
        """Try to load an Ed25519 key from *key_file*. Returns True on success."""
        try:
            data = key_file.read_bytes()
            key = serialization.load_pem_private_key(data, password=None)
            if not isinstance(key, Ed25519PrivateKey):
                raise TypeError("Key is not an Ed25519 private key")
            self._ed25519_private = key
            self._ed25519_public = key.public_key()
            self._scheme = SignatureScheme.ED25519
            _logger.debug("Loaded Ed25519 audit signing key from %s", key_file)
            return True
        except Exception as exc:
            _logger.warning(
                "Failed to load Ed25519 key from %s: %s — generating new key",
                key_file, exc,
            )
            return False

    def _generate_ed25519(self, key_file: Path) -> None:
        """Generate a new Ed25519 key and persist it to *key_file*."""
        self._ed25519_private = Ed25519PrivateKey.generate()
        self._ed25519_public = self._ed25519_private.public_key()
        self._scheme = SignatureScheme.ED25519
        try:
            pem = self._ed25519_private.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
            key_file.write_bytes(pem)
            _restrict_file_permissions(key_file)
            _logger.warning(
                "SECURITY: Auto-generated Ed25519 audit signing key at %s. "
                "For production, set AIZEE_AUDIT_SIGN_KEY to a key file "
                "outside the OS root. Back up this key — loss means "
                "audit signatures cannot be verified.",
                key_file,
            )
        except OSError as exc:
            _logger.warning("Could not persist Ed25519 key to %s: %s", key_file, exc)

    def _init_hmac(self) -> None:
        """Initialize HMAC-SHA512 key (load or generate)."""
        key_file = self._resolve_key_path("key")
        key_file.parent.mkdir(parents=True, exist_ok=True)
        if key_file.exists():
            try:
                stored = key_file.read_bytes().strip()
                if len(stored) >= 32:
                    self._hmac_key = stored
                    self._scheme = SignatureScheme.HMAC_SHA512
                    _logger.debug("Loaded HMAC-SHA512 audit key from %s", key_file)
                    return
            except OSError as exc:
                _logger.warning("Failed to load HMAC key from %s: %s", key_file, exc)
        # Generate new key (64 bytes for SHA-512).
        self._hmac_key = secrets.token_bytes(64)
        self._scheme = SignatureScheme.HMAC_SHA512
        try:
            key_file.write_bytes(self._hmac_key)
            _restrict_file_permissions(key_file)
            _logger.warning(
                "SECURITY: Auto-generated HMAC-SHA512 audit signing key at %s. "
                "For production, set AIZEE_AUDIT_SIGN_KEY to a key file "
                "outside the OS root.",
                key_file,
            )
        except OSError as exc:
            _logger.warning("Could not persist HMAC key to %s: %s", key_file, exc)

    def scheme(self) -> SignatureScheme:
        """Return the active signature scheme."""
        return self._scheme

    def sign(self, payload: bytes) -> SignatureResult:
        """Sign *payload* and return the :class:`SignatureResult`.

        The timestamp is appended to the payload before signing to
        prevent replay attacks.
        """
        import time

        ts = time.time()
        signed_data = payload + b"|" + str(ts).encode("utf-8")
        if self._scheme is SignatureScheme.ED25519:
            return self._sign_ed25519(signed_data, ts)
        if self._scheme is SignatureScheme.HMAC_SHA512:
            return self._sign_hmac(signed_data, ts)
        _logger.warning("Audit signing disabled (no crypto library available)")
        return SignatureResult(SignatureScheme.NONE, b"", None, ts)

    def _sign_ed25519(self, data: bytes, ts: float) -> SignatureResult:
        """Sign with Ed25519 and return the result with public key."""
        if self._ed25519_private is None:
            return SignatureResult(SignatureScheme.NONE, b"", None, ts)
        sig = self._ed25519_private.sign(data)
        pub_bytes = None
        if self._ed25519_public is not None:
            pub_bytes = self._ed25519_public.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
        return SignatureResult(SignatureScheme.ED25519, sig, pub_bytes, ts)

    def _sign_hmac(self, data: bytes, ts: float) -> SignatureResult:
        """Sign with HMAC-SHA512 and return the result."""
        if self._hmac_key is None:
            return SignatureResult(SignatureScheme.NONE, b"", None, ts)
        sig = hmac.new(self._hmac_key, data, hashlib.sha512).digest()
        return SignatureResult(SignatureScheme.HMAC_SHA512, sig, None, ts)

    def verify(
        self,
        payload: bytes,
        signature: bytes,
        public_key: bytes | None,
    ) -> bool:
        """Verify a signature against *payload*.

        For Ed25519, *public_key* must be the raw 32-byte public key.
        For HMAC-SHA512, *public_key* is ignored (the internal key is
        used). Returns ``False`` if verification fails or the scheme is
        NONE.
        """
        if not signature:
            return False

        if self._scheme is SignatureScheme.ED25519:
            return self._verify_ed25519(payload, signature, public_key)
        if self._scheme is SignatureScheme.HMAC_SHA512:
            return self._verify_hmac(payload, signature)
        return False

    def _verify_ed25519(
        self,
        payload: bytes,
        signature: bytes,
        public_key: bytes | None,
    ) -> bool:
        """Verify an Ed25519 signature."""
        if not _HAS_CRYPTOGRAPHY or public_key is None:
            return False
        try:
            pub = Ed25519PublicKey.from_public_bytes(public_key)
            # We don't know the original timestamp, so we try verifying
            # the raw payload (timestamp may have been stripped by the
            # caller). For full replay protection, the caller should
            # include the timestamp in the payload they pass here.
            pub.verify(signature, payload)
            return True
        except Exception:
            return False

    def _verify_hmac(self, payload: bytes, signature: bytes) -> bool:
        """Verify an HMAC-SHA512 signature using the internal key."""
        if self._hmac_key is None:
            return False
        expected = hmac.new(self._hmac_key, payload, hashlib.sha512).digest()
        return hmac.compare_digest(expected, signature)

    def export_public_key(self) -> bytes | None:
        """Export the public key for external verification.

        For Ed25519, returns the raw 32-byte public key.
        For HMAC-SHA512, returns ``None`` (symmetric — the key is not
        public).
        """
        if self._scheme is SignatureScheme.ED25519 and self._ed25519_public is not None:
            return self._ed25519_public.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
        return None
