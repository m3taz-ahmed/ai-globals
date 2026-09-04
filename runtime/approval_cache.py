#!/usr/bin/env python3
"""Session-scoped cache for explicitly approved actions."""

from __future__ import annotations

import hashlib
import json
import threading
from collections.abc import Iterable
from typing import Any


class ApprovalCache:
    """Cache of approved actions keyed by a full-action fingerprint.

    By default the key covers the ENTIRE action dict (minus volatile
    bookkeeping fields below), so approving ``ls`` cannot be replayed as
    ``ls`` with different ``args``/``env``/``flags``. Pass explicit
    ``fields`` only to opt back into legacy subset keying.

    Volatile fields excluded from the fingerprint: ``approved``, ``tokens``,
    ``cost`` (these vary per call and are enforced separately by the
    Policy ASK gate and the Budget gate).
    """

    _DEFAULT_FIELDS: tuple[str, ...] = ("type", "command", "tool", "path")
    _VOLATILE_FIELDS: frozenset[str] = frozenset({"approved", "tokens", "cost"})

    def __init__(self, fields: Iterable[str] | None = None) -> None:
        self.fields = tuple(fields) if fields is not None else None
        self._approved: set[str] = set()
        self._lock = threading.Lock()

    def _key(self, action: dict[str, Any]) -> str:
        if self.fields is None:
            subset = {k: v for k, v in action.items() if k not in self._VOLATILE_FIELDS}
        else:
            subset = {field: action.get(field) for field in self.fields}
        serialized = json.dumps(
            subset,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            default=str,
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def is_approved(self, action: dict[str, Any]) -> bool:
        """Return whether this action has already been approved."""
        with self._lock:
            return self._key(action) in self._approved

    def approve(self, action: dict[str, Any]) -> None:
        """Record this action as approved for the remainder of the session."""
        with self._lock:
            self._approved.add(self._key(action))

    def clear(self) -> None:
        """Clear all cached approvals."""
        with self._lock:
            self._approved.clear()
