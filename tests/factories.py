"""Factory functions for tests — eliminates hardcoded dates/UUIDs/tokens.

Pure functions, no classes.  Import and call wherever a test needs a
random UUID, token, timestamp, date string, memory ID, or budget dict.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import date, datetime, timedelta, timezone


def random_uuid() -> str:
    """Return a random UUID hex string."""
    return uuid.uuid4().hex


def random_token() -> str:
    """Return a random URL-safe token (16 bytes / ~22 chars)."""
    return secrets.token_urlsafe(16)


def iso_timestamp(offset_days: int = 0) -> str:
    """Return an ISO 8601 UTC timestamp, optionally offset by *offset_days*."""
    return (datetime.now(timezone.utc) + timedelta(days=offset_days)).isoformat()


def date_str(offset_days: int = 0) -> str:
    """Return an ISO date string (YYYY-MM-DD), optionally offset by *offset_days*."""
    return (date.today() + timedelta(days=offset_days)).isoformat()


def fake_memory_id() -> str:
    """Return a fake memory ID with ``mem-`` prefix and 8-char hex suffix."""
    return "mem-" + uuid.uuid4().hex[:8]


def fake_budget_dict(tokens: int = 1000, cost: float = 0.5, calls: int = 10) -> dict[str, int | float]:
    """Return a budget dict with the given token/cost/call values."""
    return {"tokens": tokens, "cost": cost, "calls": calls}
