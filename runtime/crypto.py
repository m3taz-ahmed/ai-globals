#!/usr/bin/env python3
"""At-rest encryption utilities for sensitive state files.

Uses Fernet (AES-128-CBC + HMAC-SHA256) from the ``cryptography`` package.
Key resolution: ``AIOS_ENCRYPTION_KEY`` env var, then
``AIOS_ENCRYPTION_KEY_FILE``, then an auto-generated dev key inside the OS
root (loud warning). Set ``AIOS_ENCRYPTION_KEY=plaintext`` to explicitly
disable encryption for development.

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
        try:
            return Fernet(key.encode() if isinstance(key, str) else key)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"AIOS_ENCRYPTION_KEY is not a valid Fernet key: {exc}") from exc
    # Check for external key file (production: key outside OS root)
    key_file_path = os.environ.get("AIOS_ENCRYPTION_KEY_FILE")
    if key_file_path:
        ext_path = Path(key_file_path)
        try:
            stored = ext_path.read_bytes().strip() if ext_path.is_file() else b""
        except OSError as exc:
            raise ValueError(f"Cannot read AIOS_ENCRYPTION_KEY_FILE {key_file_path}: {exc}") from exc
        if stored:
            try:
                return Fernet(stored)
            except (ValueError, TypeError) as exc:
                raise ValueError(f"AIOS_ENCRYPTION_KEY_FILE does not contain a valid Fernet key: {exc}") from exc
        raise ValueError(f"AIOS_ENCRYPTION_KEY_FILE {key_file_path} is empty or missing")
    # Auto-generate key on first run (dev fallback). Best-effort atomic:
    # concurrent processes may race, but all write valid keys and the file
    # is rewritten only when absent (O_EXCL); losers read the winner's key.
    root = Path(os.environ.get("AIZEE_ROOT", "."))
    key_file = root / "state" / ".encryption_key"
    key_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        stored = key_file.read_bytes().strip() if key_file.is_file() else b""
    except OSError:
        stored = b""
    if stored:
        try:
            return Fernet(stored)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Stored encryption key at {key_file} is invalid: {exc}") from exc
    import logging
    import platform

    generated = Fernet.generate_key()
    try:
        fd = os.open(str(key_file), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        # Lost the race — read the winner's key instead of overwriting.
        # (Nested raise: the empty-key error is a new failure, not a
        # transformation of FileExistsError — noqa B904 is intentional.)
        try:
            stored = key_file.read_bytes().strip()
        except OSError as exc:
            raise ValueError(f"Cannot read raced encryption key at {key_file}: {exc}") from exc
        if not stored:
            raise ValueError(f"Raced encryption key at {key_file} is empty")  # noqa: B904
        return Fernet(stored)
    except OSError as exc:
        raise ValueError(f"Cannot create encryption key file {key_file}: {exc}") from exc
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(generated)
    except OSError as exc:
        raise ValueError(f"Cannot write encryption key file {key_file}: {exc}") from exc
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
    try:
        if not path.is_file():
            return False
        with open(path, "rb") as f:
            return f.read(len(_MAGIC)) == _MAGIC
    except OSError:
        return False


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
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ValueError(f"Cannot read file {path}: {exc}") from exc
    decrypted = decrypt_bytes(data)
    try:
        return decrypted.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"File {path} is not valid UTF-8: {exc}") from exc


def generate_key() -> str:
    """Generate a new Fernet key for use as AIOS_ENCRYPTION_KEY."""
    return Fernet.generate_key().decode("utf-8")
