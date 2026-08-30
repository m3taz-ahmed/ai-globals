#!/usr/bin/env python3
"""Append-only audit logging with HMAC hash chaining for aiZee.

Each log entry is cryptographically chained to the previous one via
HMAC-SHA-256, producing a tamper-evident trail. Any modification or
deletion of a past entry breaks the chain and is detectable via
``verify_chain()``.
"""

from __future__ import annotations

import contextlib
import hashlib
import hmac
import json
import logging
import os
import platform
import re
import secrets
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_logger = logging.getLogger(__name__)

_SENSITIVE_KEYS = re.compile(r"(token|key|secret|password|credential|auth|api[_-]?key)", re.IGNORECASE)

_GENESIS_HASH = "0" * 64

# Module-level cache for the audit HMAC key (B6).
_audit_key_cache: bytes | None = None
_audit_key_lock = threading.Lock()


def _restrict_file_permissions(path: Path) -> None:
    """Restrict file permissions to 0o600 (owner-only), cross-platform."""
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


def _get_audit_key() -> bytes:
    """Return the HMAC key for audit chain integrity (B6).

    Resolution order:
    1. ``AIZEE_AUDIT_KEY`` env var (raw key bytes).
    2. ``AIZEE_AUDIT_KEY_FILE`` env var (path to a file containing the key).
    3. Auto-generated random key stored in ``state/audit.key`` (0o600).

    The key is cached in a module-level variable after first resolution.
    """
    global _audit_key_cache
    with _audit_key_lock:
        if _audit_key_cache is not None:
            return _audit_key_cache
        # 1. Env var with raw key.
        env_key = os.environ.get("AIZEE_AUDIT_KEY")
        if env_key:
            _audit_key_cache = env_key.encode("utf-8")
            return _audit_key_cache
        # 2. Env var with key file path.
        key_file_env = os.environ.get("AIZEE_AUDIT_KEY_FILE")
        if key_file_env:
            key_path = Path(key_file_env)
            if key_path.exists():
                stored = key_path.read_bytes().strip()
                if stored:
                    _audit_key_cache = stored
                    return _audit_key_cache
        # 3. Auto-generate and persist to state/audit.key.
        root = Path(os.environ.get("AIZEE_ROOT", "."))
        key_file = root / "state" / "audit.key"
        key_file.parent.mkdir(parents=True, exist_ok=True)
        if key_file.exists():
            stored = key_file.read_bytes().strip()
            if stored:
                _audit_key_cache = stored
                return _audit_key_cache
        generated = secrets.token_bytes(32)
        key_file.write_bytes(generated)
        _restrict_file_permissions(key_file)
        _logger.warning(
            "SECURITY: No AIZEE_AUDIT_KEY set — auto-generated audit HMAC key "
            "stored at %s. For production, set AIZEE_AUDIT_KEY env var or "
            "AIZEE_AUDIT_KEY_FILE to a path outside the OS root. "
            "Back up this file — loss means the audit chain cannot be verified.",
            key_file,
        )
        _audit_key_cache = generated
        return _audit_key_cache


def _ts_after(entry_ts: str, since_ts: str) -> bool:
    """Return True if ``entry_ts`` is at or after ``since_ts``.

    Parses both as ISO-8601 datetimes (handling ``Z`` suffix and offsets) so
    mixed timezone formats compare correctly. Falls back to string comparison
    if either value fails to parse.
    """
    try:
        from datetime import datetime as _dt

        def _parse(ts: str) -> _dt:
            # Normalize trailing Z to +00:00 for fromisoformat.
            if ts.endswith("Z"):
                ts = ts[:-1] + "+00:00"
            parsed = _dt.fromisoformat(ts)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed

        return _parse(entry_ts) >= _parse(since_ts)
    except (ValueError, TypeError):
        return entry_ts >= since_ts


class AuditLogger:
    """Append-only, HMAC hash-chained audit log for policy, budget, and workflow events.

    Every entry stores ``prev_hash`` (the hash of the preceding entry) and
    ``hash`` (HMAC-SHA-256 of its own canonical JSON excluding the ``hash``
    field, keyed via ``_get_audit_key``). The first entry's ``prev_hash``
    is the genesis hash (64 zeros).
    """

    _MAX_LOG_SIZE = 100 * 1024 * 1024  # 100 MB
    _MAX_ROTATED = 5

    def __init__(self, root: Path) -> None:
        self.root = root
        self.log_file = root / "state" / "audit.log"
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        # Cache last hash in memory to avoid O(n) file scan on every log() call.
        # Initialized lazily on first use; invalidated only on rotation.
        self._cached_last_hash: str | None = None
        self._cache_lock = threading.Lock()

    def _rotate_if_needed(self) -> None:
        """Rotate the audit log if it exceeds the max size."""
        try:
            if self.log_file.exists() and self.log_file.stat().st_size > self._MAX_LOG_SIZE:
                # Rotate: audit.log -> audit.log.1, audit.log.1 -> audit.log.2, etc.
                for i in range(self._MAX_ROTATED - 1, 0, -1):
                    old = self.log_file.with_suffix(f".log.{i}")
                    new = self.log_file.with_suffix(f".log.{i + 1}")
                    if old.exists():
                        old.rename(new)
                rotated = self.log_file.with_suffix(".log.1")
                self.log_file.rename(rotated)
                # Invalidate cache after rotation — new file starts from genesis
                with self._cache_lock:
                    self._cached_last_hash = None
        except OSError as exc:
            # L2: log rotation failures so operators notice disk/permission
            # issues instead of silently losing the audit trail.
            _logger.warning("Audit log rotation failed: %s", exc)

    def _redact(self, value: Any, key_name: str = "") -> Any:
        """Redact sensitive values using both key-name and content matching.

        - If the key name matches a sensitive pattern, the entire value is redacted.
        - If the value (string) contains a sensitive keyword, it is redacted.
        - Recursively processes dicts and lists.
        """
        # Key-based redaction: if the key name looks sensitive, redact entire value
        if key_name and _SENSITIVE_KEYS.search(key_name):
            return "[REDACTED]"
        if isinstance(value, dict):
            return {k: self._redact(v, key_name=k) for k, v in value.items()}
        if isinstance(value, list):
            return [self._redact(v, key_name=key_name) for v in value]
        if isinstance(value, str) and _SENSITIVE_KEYS.search(value):
            return "[REDACTED]"
        return value

    def _last_hash(self) -> str:
        """Return the hash of the last entry in the log, or genesis if empty.

        Uses in-memory cache for O(1) after first read; falls back to
        tail-scan only on cache-miss (first init or after rotation).

        The tail-scan reads the last line in full by scanning backward for the
        final newline, growing the read window up to the whole file. This
        avoids the previous 8KB cap which truncated large JSON records
        (>8KB) mid-entry, causing ``json.loads`` to fail and silently breaking
        the hash chain (returning genesis instead of the real last hash).
        """
        with self._cache_lock:
            if self._cached_last_hash is not None:
                return self._cached_last_hash
        if not self.log_file.exists():
            return _GENESIS_HASH
        last_line: str | None = None
        try:
            with self.log_file.open("rb") as f:
                f.seek(0, 2)
                size = f.tell()
                if size == 0:
                    return _GENESIS_HASH
                # Scan backward from EOF to find the last complete line.
                # Start with 8KB but grow up to the full file size if the last
                # record is larger than the initial window.
                window = min(size, 8192)
                pos = size - window
                while True:
                    f.seek(pos)
                    chunk = f.read(size - pos).decode("utf-8", errors="ignore")
                    lines = [ln.strip() for ln in chunk.splitlines() if ln.strip()]
                    if lines:
                        # If we read from the very start, lines[0] is complete.
                        # Otherwise lines[0] is a partial line (mid-record) and
                        # we must use lines[1:] — but the LAST line is always
                        # complete because the file ends with it.
                        last_line = lines[-1]
                        break
                    # No complete line in this window; grow toward the start.
                    if pos == 0:
                        break
                    window = min(size, window * 4)
                    pos = max(0, size - window)
        except OSError:
            # Fallback to full scan on error
            with self.log_file.open("r", encoding="utf-8") as fh:
                for line in fh:
                    stripped = line.strip()
                    if stripped:
                        last_line = stripped
        if last_line is None:
            return _GENESIS_HASH
        try:
            entry = json.loads(last_line)
            h = str(entry.get("hash", _GENESIS_HASH))
            with self._cache_lock:
                self._cached_last_hash = h
            return h
        except (json.JSONDecodeError, KeyError):
            return _GENESIS_HASH

    @staticmethod
    def _compute_hash(entry: dict[str, Any]) -> str:
        """Compute HMAC-SHA-256 hash of an entry excluding the ``hash`` field (B6).

        Uses a secret key (from ``_get_audit_key``) so that an attacker who
        can read the log but not the key cannot forge a valid chain link.
        """
        payload = {k: v for k, v in entry.items() if k != "hash"}
        canonical = json.dumps(payload, sort_keys=True, default=str)
        key = _get_audit_key()
        return hmac.new(key, canonical.encode("utf-8"), hashlib.sha256).hexdigest()

    def log(self, event_type: str, details: dict[str, Any]) -> None:
        """Append a new hash-chained entry to the audit log.

        Fail-open: if the audit log cannot be written (disk full, permission
        error, etc.), the error is logged but NOT raised. Observability must
        never crash the agent.
        """
        with self._lock:
            try:
                self._rotate_if_needed()
                prev_hash = self._last_hash()
                entry: dict[str, Any] = {
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "type": event_type,
                    "details": self._redact(details),
                    "prev_hash": prev_hash,
                }
                entry["hash"] = self._compute_hash(entry)
                with self.log_file.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, default=str) + "\n")
                # Update cache with the new hash for O(1) next call
                with self._cache_lock:
                    self._cached_last_hash = entry["hash"]
            except OSError as exc:
                _logger.error(
                    "Audit log write failed (fail-open): %s — event_type=%s",
                    exc, event_type,
                )
                if os.environ.get("AIZEE_AUDIT_STRICT"):
                    raise

    def log_admission(self, record: dict[str, Any]) -> None:
        """Append an admission event with identity keys (Hazem R1-R15).

        Stores the four identity keys (context_hash, runtime_key, output_key,
        promotion lineage) so an incident can be replayed from evidence
        records without retaining raw sensitive payloads. Sensitive keys
        are redacted via ``_redact`` before hashing.
        """
        details = {
            "request_id": record.get("request_id", ""),
            "context_hash": record.get("context_hash", ""),
            "runtime_key": record.get("runtime_key", ""),
            "output_key": record.get("output_key", ""),
            "stop_reason": record.get("stop_reason", ""),
            "schema_valid": record.get("schema_valid", False),
            "evidence_coverage": record.get("evidence_coverage", 0.0),
            "policy_verdict": record.get("policy_verdict", ""),
            "admission_policy": record.get("admission_policy", ""),
            "decision": record.get("decision", ""),
            "reason_code": record.get("reason_code", ""),
            "tenant_id": record.get("tenant_id", ""),
        }
        self.log("admission", details)

    def log_authorization(self, record: dict[str, Any]) -> None:
        """Append an authorization decision event (Hazem zero-trust PDP/PEP).

        Stores the authorization tuple hash, decision, obligations, and
        receipt linkage so an auditor can reconstruct proposal, decision,
        and consequence from evidence.
        """
        details = {
            "decision_id": record.get("decision_id", ""),
            "tuple_hash": record.get("tuple_hash", ""),
            "subject_id": record.get("subject_id", ""),
            "tenant_id": record.get("tenant_id", ""),
            "workload_id": record.get("workload_id", ""),
            "operation_id": record.get("operation_id", ""),
            "target_id": record.get("target_id", ""),
            "decision": record.get("decision", ""),
            "reason": record.get("reason", ""),
            "obligations": record.get("obligations", []),
            "idempotency_key": record.get("idempotency_key", ""),
            "receipt_id": record.get("receipt_id", ""),
        }
        self.log("authorization", details)

    def verify_chain(self) -> dict[str, Any]:
        """Verify the integrity of the HMAC hash chain (B6).

        Walks the audit log and verifies each entry's HMAC and prev_hash
        linkage. Logs errors but does not crash.

        Returns a dict with ``valid`` (bool), ``entries_checked`` (int),
        and ``broken_at`` (int | None, the 0-based index of the first
        broken link, or ``None`` if the chain is intact).
        """
        if not self.log_file.exists():
            return {"valid": True, "entries_checked": 0, "broken_at": None}
        expected_prev = _GENESIS_HASH
        idx = 0
        broken_at: int | None = None
        try:
            with self.log_file.open("r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    try:
                        entry = json.loads(stripped)
                    except json.JSONDecodeError as exc:
                        _logger.error(
                            "Audit chain broken at entry %d: JSON decode error: %s",
                            idx, exc,
                        )
                        broken_at = broken_at if broken_at is not None else idx
                        break
                    # Check prev_hash linkage
                    if entry.get("prev_hash") != expected_prev:
                        _logger.error(
                            "Audit chain broken at entry %d: prev_hash mismatch "
                            "(expected %s, got %s)",
                            idx, expected_prev, entry.get("prev_hash"),
                        )
                        broken_at = broken_at if broken_at is not None else idx
                        break
                    # Recompute and verify HMAC
                    recomputed = self._compute_hash(entry)
                    if recomputed != entry.get("hash"):
                        _logger.error(
                            "Audit chain broken at entry %d: HMAC mismatch "
                            "(recomputed %s, stored %s)",
                            idx, recomputed, entry.get("hash"),
                        )
                        broken_at = broken_at if broken_at is not None else idx
                        break
                    expected_prev = str(entry.get("hash", ""))
                    idx += 1
        except OSError as exc:
            _logger.error("Audit chain verification failed (I/O error): %s", exc)
            return {"valid": False, "entries_checked": idx, "broken_at": broken_at}
        if broken_at is not None:
            _logger.warning(
                "Audit chain integrity check FAILED at entry %d (%d entries checked)",
                broken_at, idx,
            )
        else:
            _logger.info("Audit chain integrity OK (%d entries checked)", idx)
        return {
            "valid": broken_at is None,
            "entries_checked": idx,
            "broken_at": broken_at,
        }

    def read_entries(
        self,
        event_type: str | None = None,
        limit: int = 50,
        since: str | None = None,
    ) -> list[dict[str, Any]]:
        """Read audit log entries with optional filtering.

        Args:
            event_type: Filter by event type (e.g., 'policy', 'budget').
            limit: Maximum number of entries to return (most recent first).
            since: ISO timestamp â€” only entries after this time are returned.
        """
        if not self.log_file.exists():
            return []
        entries: list[dict[str, Any]] = []
        with self.log_file.open("r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    entry = json.loads(stripped)
                except json.JSONDecodeError:
                    continue
                if event_type and entry.get("type") != event_type:
                    continue
                # L3: compare timestamps as datetime objects, not raw strings,
                # so mixed timezone formats (Z vs +00:00 vs local) compare
                # correctly. Fall back to string comparison on parse failure.
                if since:
                    entry_ts = entry.get("ts", "")
                    if not _ts_after(entry_ts, since):
                        continue
                entries.append(entry)
        return list(reversed(entries[-limit:]))
