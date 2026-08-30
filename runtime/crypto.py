#!/usr/bin/env python3
"""At-rest encryption utilities for sensitive state files.

Uses Fernet (AES-128-CBC + HMAC-SHA256) from the ``cryptography`` package.
The encryption key is read from the ``AIOS_ENCRYPTION_KEY`` environment
variable. When the key is not set, encryption is disabled (plaintext mode)
to maintain backward compatibility and zero-config startup.

Usage::

    from runtime.crypto import encrypt_file, decrypt_file

    encrypt_file(path)   # encrypts in-place if key is set
    decrypt_file(path)   # decrypts in-place if key is set, returns original if not
"""

from __future__ import annotations

import contextlib
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

_MAGIC = b"AIOS_ENC:"  # 9-byte magic prefix to detect encrypted files


def _get_fernet() -> Fernet | None:
    """Return a Fernet instance. Auto-generates a key if none is set (secure-by-default).

    Key resolution order:
    1. ``AIOS_ENCRYPTION_KEY`` env var (production — key never touches disk).
    2. ``AIOS_ENCRYPTION_KEY_FILE`` env var (path outside OS root, e.g. ``/etc/aizee/enc.key``).
    3. Auto-generated key in ``state/.encryption_key`` (dev only — warns loudly).

    Set AIOS_ENCRYPTION_KEY=plaintext to explicitly disable encryption.
    """
    key = os.environ.get("AIOS_ENCRYPTION_KEY")
    if key == "plaintext":
        return None  # Explicit opt-out for development
    if key:
        return Fernet(key.encode() if isinstance(key, str) else key)
    # Check for external key file (production: key outside OS root)
    key_file_path = os.environ.get("AIOS_ENCRYPTION_KEY_FILE")
    if key_file_path:
        ext_path = Path(key_file_path)
        if ext_path.exists():
            stored = ext_path.read_bytes().strip()
            if stored:
                return Fernet(stored)
    # Auto-generate key on first run (dev fallback)
    root = Path(os.environ.get("AIZEE_ROOT", "."))
    key_file = root / "state" / ".encryption_key"
    key_file.parent.mkdir(parents=True, exist_ok=True)
    if key_file.exists():
        stored = key_file.read_bytes().strip()
        if stored:
            return Fernet(stored)
    import logging
    import platform

    generated = Fernet.generate_key()
    key_file.write_bytes(generated)
    try:
        if platform.system() == "Windows":
            # On Windows, chmod is a no-op; restrict via ACL if icacls is available
            import getpass
            import subprocess

            try:
                user = os.getlogin()
            except OSError:
                user = getpass.getuser()
            subprocess.run(
                ["icacls", str(key_file), "/inheritance:r", "/grant:r", f"{user}:(R,W)"],
                capture_output=True,
                timeout=5,
                check=False,
            )
        else:
            key_file.chmod(0o600)
    except Exception:
        with contextlib.suppress(OSError):
            key_file.chmod(0o600)
    logging.getLogger(__name__).warning(
        "SECURITY: No AIOS_ENCRYPTION_KEY set — auto-generated key stored at %s "
        "INSIDE the OS root. For production, set AIOS_ENCRYPTION_KEY env var or "
        "AIOS_ENCRYPTION_KEY_FILE to a path outside the OS root. "
        "Back up this file — loss means encrypted state is unrecoverable.",
        key_file,
    )
    return Fernet(generated)


def is_encrypted(path: Path) -> bool:
    """Check if a file starts with the encryption magic prefix."""
    if not path.exists():
        return False
    with open(path, "rb") as f:
        return f.read(len(_MAGIC)) == _MAGIC


def encrypt_bytes(data: bytes) -> bytes:
    """Encrypt bytes if key is set, return original if not."""
    f = _get_fernet()
    if f is None:
        return data
    return _MAGIC + f.encrypt(data)


def decrypt_bytes(data: bytes) -> bytes:
    """Decrypt bytes if encrypted and key is set, return original if not."""
    if not data.startswith(_MAGIC):
        return data
    f = _get_fernet()
    if f is None:
        raise ValueError("File is encrypted but AIOS_ENCRYPTION_KEY is not set")
    try:
        return f.decrypt(data[len(_MAGIC):])
    except InvalidToken as exc:
        raise ValueError("Invalid encryption key or corrupted data") from exc


def encrypt_file(path: Path) -> None:
    """Encrypt a file in-place if key is set and file is not already encrypted."""
    f = _get_fernet()
    if f is None:
        return
    if not path.exists() or is_encrypted(path):
        return
    data = path.read_bytes()
    encrypted = _MAGIC + f.encrypt(data)
    path.write_bytes(encrypted)


def decrypt_file(path: Path) -> str:
    """Read and decrypt a file, returning its text content.

    If the file is not encrypted or no key is set, returns plaintext.
    """
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    data = path.read_bytes()
    decrypted = decrypt_bytes(data)
    return decrypted.decode("utf-8")


def generate_key() -> str:
    """Generate a new Fernet key for use as AIOS_ENCRYPTION_KEY."""
    return Fernet.generate_key().decode("utf-8")
