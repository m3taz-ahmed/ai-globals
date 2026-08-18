#!/usr/bin/env python3
"""Append-only audit logging with hash chaining for aiZee.

Each log entry is cryptographically chained to the previous one via SHA-256,
producing a tamper-evident trail. Any modification or deletion of a past
entry breaks the chain and is detectable via ``verify_chain()``.
"""

from __future__ import annotations

import hashlib
import json
import re
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_SENSITIVE_KEYS = re.compile(r"(token|key|secret|password|credential|auth|api[_-]?key)", re.IGNORECASE)

_GENESIS_HASH = "0" * 64


class AuditLogger:
    """Append-only, hash-chained audit log for policy, budget, and workflow events.

    Every entry stores ``prev_hash`` (the hash of the preceding entry) and
    ``hash`` (SHA-256 of its own canonical JSON excluding the ``hash`` field).
    The first entry's ``prev_hash`` is the genesis hash (64 zeros).
    """

    _MAX_LOG_SIZE = 100 * 1024 * 1024  # 100 MB
    _MAX_ROTATED = 5

    def __init__(self, root: Path) -> None:
        self.root = root
        self.log_file = root / "state" / "audit.log"
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

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
        except OSError:
            pass  # Best-effort rotation

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
        """Return the hash of the last entry in the log, or genesis if empty."""
        if not self.log_file.exists():
            return _GENESIS_HASH
        last_line: str | None = None
        with self.log_file.open("r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    last_line = stripped
        if last_line is None:
            return _GENESIS_HASH
        try:
            entry = json.loads(last_line)
            return str(entry.get("hash", _GENESIS_HASH))
        except (json.JSONDecodeError, KeyError):
            return _GENESIS_HASH

    @staticmethod
    def _compute_hash(entry: dict[str, Any]) -> str:
        """Compute SHA-256 hash of an entry excluding the ``hash`` field."""
        payload = {k: v for k, v in entry.items() if k != "hash"}
        canonical = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def log(self, event_type: str, details: dict[str, Any]) -> None:
        """Append a new hash-chained entry to the audit log."""
        with self._lock:
            self._rotate_if_needed()
            prev_hash = self._last_hash()
            entry: dict[str, Any] = {
                "ts": datetime.now(UTC).isoformat(),
                "type": event_type,
                "details": self._redact(details),
                "prev_hash": prev_hash,
            }
            entry["hash"] = self._compute_hash(entry)
            with self.log_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, default=str) + "\n")

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
        """Verify the integrity of the hash chain.

        Returns a dict with ``valid`` (bool), ``entries_checked`` (int),
        and ``broken_at`` (int | None, the 0-based index of the first
        broken link, or ``None`` if the chain is intact).
        """
        if not self.log_file.exists():
            return {"valid": True, "entries_checked": 0, "broken_at": None}
        expected_prev = _GENESIS_HASH
        idx = 0
        broken_at: int | None = None
        with self.log_file.open("r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    entry = json.loads(stripped)
                except json.JSONDecodeError:
                    broken_at = broken_at if broken_at is not None else idx
                    break
                # Check prev_hash linkage
                if entry.get("prev_hash") != expected_prev:
                    broken_at = broken_at if broken_at is not None else idx
                    break
                # Recompute and verify hash
                recomputed = self._compute_hash(entry)
                if recomputed != entry.get("hash"):
                    broken_at = broken_at if broken_at is not None else idx
                    break
                expected_prev = str(entry.get("hash", ""))
                idx += 1
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
            since: ISO timestamp — only entries after this time are returned.
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
                if since and entry.get("ts", "") < since:
                    continue
                entries.append(entry)
        return list(reversed(entries[-limit:]))
