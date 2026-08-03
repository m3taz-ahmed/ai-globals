#!/usr/bin/env python3
"""Session-scoped cache for explicitly approved actions."""

from __future__ import annotations

import hashlib
import json
import threading
from collections.abc import Iterable
from typing import Any


class ApprovalCache:
    """Cache of approved actions keyed by a normalized subset of fields.

    The default key fields are ``type``, ``command``, ``tool`` and ``path``.
    A stable JSON serialization + SHA-256 hash is used so equivalent actions
    produce identical keys regardless of dict ordering or extra fields.
    """

    _DEFAULT_FIELDS: tuple[str, ...] = ("type", "command", "tool", "path")

    def __init__(self, fields: Iterable[str] | None = None) -> None:
        self.fields = tuple(fields) if fields is not None else self._DEFAULT_FIELDS
        self._approved: set[str] = set()
        self._lock = threading.Lock()

    def _key(self, action: dict[str, Any]) -> str:
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
        return self._key(action) in self._approved

    def approve(self, action: dict[str, Any]) -> None:
        """Record this action as approved for the remainder of the session."""
        with self._lock:
            self._approved.add(self._key(action))

    def clear(self) -> None:
        """Clear all cached approvals."""
        with self._lock:
            self._approved.clear()
