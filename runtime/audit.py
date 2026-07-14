#!/usr/bin/env python3
"""Audit logging for AI Global OS."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AuditLogger:
    """Append-only audit log for policy, budget, and workflow events."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.log_file = root / "state" / "audit.log"
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log(self, event_type: str, details: dict[str, Any]) -> None:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "type": event_type,
            "details": details,
        }
        with self.log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")
