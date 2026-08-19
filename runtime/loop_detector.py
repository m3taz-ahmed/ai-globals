#!/usr/bin/env python3
"""Hash-based loop detection for aiZee actions.

Inspired by Omnigent's loop detection: every action is hashed by
``{tool_name, key_args}`` and tracked in a bounded deque. When the same
hash repeats within the window, the action is blocked as a suspected
infinite loop.

This is a pre-action safety layer that runs *before* the guardian/policy
gates. It is per-session (or per-kernel-instance) and thread-safe.

Usage::

    from runtime.loop_detector import LoopDetector
    detector = LoopDetector(window=10)
    if detector.is_looping("exec_shell", {"command": "ls"}):
        raise PolicyDeniedError("LOOP_DETECTED", "repeated action blocked")
    detector.record("exec_shell", {"command": "ls"})
"""

from __future__ import annotations

import hashlib
import json
import threading
from collections import deque
from dataclasses import dataclass
from typing import Any


def _action_hash(tool: str, args: dict[str, Any]) -> str:
    """Stable hash of a tool call. Args are sorted for determinism."""
    payload = json.dumps({"tool": tool, "args": args}, sort_keys=True, default=str)
    return hashlib.md5(payload.encode("utf-8")).hexdigest()


@dataclass
class LoopHit:
    """Details of a detected loop."""

    tool: str
    args: dict[str, Any]
    hash_value: str
    repeat_count: int
    window: int


class LoopDetector:
    """Detect repeated actions within a sliding window.

    Attributes:
        window: Number of recent actions to track (default 10).
        threshold: Number of repeats before blocking (default 2 — block on
            the second occurrence, matching Omnigent's behavior).
    """

    def __init__(self, window: int = 10, threshold: int = 2) -> None:
        if window < 1:
            raise ValueError("window must be >= 1")
        if threshold < 2:
            raise ValueError("threshold must be >= 2")
        self.window = window
        self.threshold = threshold
        self._history: deque[str] = deque(maxlen=window)
        self._counts: dict[str, int] = {}
        self._lock = threading.RLock()
        self._blocks: int = 0

    def _count_in_window(self, h: str) -> int:
        """Count occurrences of hash h in the current window."""
        return sum(1 for x in self._history if x == h)

    def is_looping(self, tool: str, args: dict[str, Any]) -> bool:
        """Check if recording this action would trigger a loop.

        Does NOT record the action — call ``record`` after a successful
        action, or call ``check_and_record`` to do both atomically.
        """
        h = _action_hash(tool, args)
        with self._lock:
            return self._count_in_window(h) >= self.threshold - 1

    def check_and_record(self, tool: str, args: dict[str, Any]) -> LoopHit | None:
        """Atomically check + record. Returns LoopHit if blocked, None if ok."""
        h = _action_hash(tool, args)
        with self._lock:
            current = self._count_in_window(h)
            if current >= self.threshold - 1:
                self._blocks += 1
                return LoopHit(
                    tool=tool,
                    args=args,
                    hash_value=h,
                    repeat_count=current + 1,
                    window=self.window,
                )
            self._history.append(h)
            return None

    def record(self, tool: str, args: dict[str, Any]) -> None:
        """Record an action without checking. Useful for seeding history."""
        h = _action_hash(tool, args)
        with self._lock:
            self._history.append(h)

    def reset(self) -> None:
        """Clear history (e.g. on new session)."""
        with self._lock:
            self._history.clear()
            self._counts.clear()

    @property
    def blocks(self) -> int:
        """Total number of loop blocks since creation."""
        return self._blocks

    @property
    def size(self) -> int:
        """Current history size."""
        return len(self._history)

    def stats(self) -> dict[str, int]:
        """Return a stats dict for observability."""
        with self._lock:
            return {
                "window": self.window,
                "threshold": self.threshold,
                "size": len(self._history),
                "blocks": self._blocks,
                "unique_hashes": len(set(self._history)),
            }
