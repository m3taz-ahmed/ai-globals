#!/usr/bin/env python3
"""Audit logging for AI Global OS."""

from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SENSITIVE_KEYS = re.compile(r"(token|key|secret|password|credential|auth|api[_-]?key)", re.IGNORECASE)


class AuditLogger:
    """Append-only audit log for policy, budget, and workflow events."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.log_file = root / "state" / "audit.log"
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _redact(self, value: Any) -> Any:
        """Redact likely sensitive strings and recursively process containers."""
        if isinstance(value, dict):
            return {k: self._redact(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._redact(v) for v in value]
        if isinstance(value, str) and _SENSITIVE_KEYS.search(value):
            return "[REDACTED]"
        return value

    def log(self, event_type: str, details: dict[str, Any]) -> None:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "type": event_type,
            "details": self._redact(details),
        }
        with self._lock, self.log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")
