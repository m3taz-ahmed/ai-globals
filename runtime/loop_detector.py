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
from enum import Enum
from typing import Any, Final


class LoopAction(str, Enum):
    """Escalation actions for graduated loop response (from agent-loop-guard)."""

    CONTINUE = "continue"
    WARN = "warn"
    STOP = "stop"
    ESCALATE = "escalate"


@dataclass
class ActionConfig:
    """Thresholds for action escalation (from agent-loop-guard).

    Consecutive loop hits escalate the action:
    - hits < warn_threshold → CONTINUE
    - warn_threshold <= hits < stop_threshold → WARN
    - stop_threshold <= hits < escalate_threshold → STOP
    - hits >= escalate_threshold → ESCALATE
    """

    warn_threshold: int = 2
    stop_threshold: int = 4
    escalate_threshold: int = 6


# Fields that legitimately vary between otherwise-identical actions
# (token counts, cost, approval flags, session ids). Excluded from the
# loop hash so an attacker cannot evade detection by toggling them (B8).
_VOLATILE_KEYS: Final[frozenset[str]] = frozenset(
    {
        "tokens",
        "cost",
        "approved",
        "dry_run",
        "token_weight",
        "input_tokens",
        "output_tokens",
        "rollout_id",
        "session_id",
    }
)


def _action_hash(tool: str, args: dict[str, Any]) -> str:
    """Stable hash of a tool call. Args are sorted for determinism.

    Volatile fields (tokens, cost, approval flags, session ids) are excluded
    so that logically-identical actions are still detected as loops even when
    their accounting metadata differs (B8).
    """
    stable_args = {k: v for k, v in args.items() if k not in _VOLATILE_KEYS}
    payload = json.dumps({"tool": tool, "args": stable_args}, sort_keys=True, default=str)
    return hashlib.md5(payload.encode("utf-8")).hexdigest()


def _jaccard_similarity(set_a: set[str], set_b: set[str]) -> float:
    """Jaccard similarity between two sets (from agent-loop-guard)."""
    if not set_a and not set_b:
        return 1.0
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


def _args_to_set(args: dict[str, Any]) -> set[str]:
    """Convert args dict to a set of string representations for Jaccard."""
    result: set[str] = set()
    for k, v in args.items():
        result.add(f"{k}={v}")
    return result


def _edit_distance(s1: str, s2: str) -> int:
    """Levenshtein edit distance between two strings."""
    if len(s1) < len(s2):
        return _edit_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            curr_row.append(min(
                prev_row[j + 1] + 1,
                curr_row[j] + 1,
                prev_row[j] + (c1 != c2),
            ))
        prev_row = curr_row
    return prev_row[-1]


def _args_similarity(args1: dict[str, Any], args2: dict[str, Any]) -> float:
    """Combined similarity score between two args dicts (Jaccard + edit distance).

    Returns a float in [0, 1] where 1.0 means identical.
    Bounds Levenshtein cost: when serialized JSON exceeds 20KB, falls back
    to Jaccard-only (exact path) to avoid O(n·m) blowup.
    """
    set1 = _args_to_set(args1)
    set2 = _args_to_set(args2)
    jaccard = _jaccard_similarity(set1, set2)
    # Also compare stringified versions for edit distance
    s1 = json.dumps(args1, sort_keys=True, default=str)
    s2 = json.dumps(args2, sort_keys=True, default=str)
    if not s1 and not s2:
        return 1.0
    # Bound cost: skip edit distance on large payloads, use Jaccard only.
    if len(s1) > 20_000 or len(s2) > 20_000:
        return jaccard
    max_len = max(len(s1), len(s2))
    if max_len == 0:
        return 1.0
    edit_dist = _edit_distance(s1, s2)
    edit_sim = 1.0 - (edit_dist / max_len)
    return (jaccard + edit_sim) / 2.0


@dataclass
class LoopHit:
    """Details of a detected loop."""

    tool: str
    args: dict[str, Any]
    hash_value: str
    repeat_count: int
    window: int
    detection: str = "exact"  # "exact", "fuzzy", "cycle"
    similarity: float = 1.0
    action: LoopAction = LoopAction.STOP
    consecutive_hits: int = 1


class LoopDetector:
    """Detect repeated actions within a sliding window.

    Supports four detection strategies (from agent-loop-guard):
    1. Exact repeat — same hash appears >= threshold times
    2. Fuzzy repeat — args similarity >= fuzzy_threshold (Jaccard + edit distance)
    3. Cycle detection — repeating sequence A→B→C→A
    4. Action escalation — consecutive hits escalate CONTINUE→WARN→STOP→ESCALATE

    Attributes:
        window: Number of recent actions to track (default 10).
        threshold: Number of exact repeats before blocking (default 2).
        fuzzy_threshold: Similarity score for fuzzy matching (default 0.85).
        fuzzy_enabled: Whether fuzzy matching is active (default True).
        cycle_min_repeats: Minimum sequence repeats for cycle detection (default 3).
        cycle_enabled: Whether cycle detection is active (default True).
        action_config: Thresholds for action escalation.
    """

    def __init__(
        self,
        window: int = 10,
        threshold: int = 2,
        fuzzy_threshold: float = 0.85,
        fuzzy_enabled: bool = True,
        cycle_min_repeats: int = 3,
        cycle_enabled: bool = True,
        action_config: ActionConfig | None = None,
    ) -> None:
        if window < 1:
            raise ValueError("window must be >= 1")
        if threshold < 2:
            raise ValueError("threshold must be >= 2")
        self.window = window
        self.threshold = threshold
        self.fuzzy_threshold = fuzzy_threshold
        self.fuzzy_enabled = fuzzy_enabled
        self.cycle_min_repeats = cycle_min_repeats
        self.cycle_enabled = cycle_enabled
        self.action_config = action_config or ActionConfig()
        self._history: deque[str] = deque(maxlen=window)
        # Track (tool, args) pairs for fuzzy and cycle detection
        self._tool_history: deque[tuple[str, dict[str, Any]]] = deque(maxlen=window)
        self._lock = threading.RLock()
        self._blocks: int = 0
        self._consecutive_hits: int = 0

    def _count_in_window(self, h: str) -> int:
        """Count occurrences of hash h in the current window."""
        return sum(1 for x in self._history if x == h)

    def _detect_fuzzy(self, tool: str, args: dict[str, Any]) -> tuple[float, dict[str, Any]] | None:
        """Check for fuzzy repeat — requires >=2 similar past actions.

        Falls back to exact-only (None) when history exceeds 200 entries
        to bound O(n) scan cost.
        """
        if not self.fuzzy_enabled:
            return None
        if len(self._tool_history) > 200:
            return None
        best_sim = 0.0
        best_args: dict[str, Any] = {}
        similar_count = 0
        for past_tool, past_args in self._tool_history:
            if past_tool != tool:
                continue
            sim = _args_similarity(args, past_args)
            if sim >= self.fuzzy_threshold:
                similar_count += 1
                if sim > best_sim:
                    best_sim = sim
                    best_args = past_args
        # Single-similar firing is too strict (false positives on retries);
        # require at least 2 similar past actions.
        if similar_count >= 2 and best_sim > 0:
            return best_sim, best_args
        return None

    def _detect_cycle(self, tool: str, args: dict[str, Any]) -> bool:
        """Check for repeating sequence (e.g., A→B→C→A→B→C→A)."""
        if not self.cycle_enabled:
            return False
        history_list = list(self._tool_history)
        # Append the current action to check
        history_list.append((tool, args))
        n = len(history_list)
        # Try cycle lengths from 2 to n//cycle_min_repeats
        max_cycle_len = n // self.cycle_min_repeats
        for cycle_len in range(2, max_cycle_len + 1):
            repeats = n // cycle_len
            if repeats < self.cycle_min_repeats:
                continue
            # Check if the last `repeats * cycle_len` items form a repeating cycle
            segment = history_list[-(repeats * cycle_len):]
            pattern = segment[:cycle_len]
            is_cycle = all(
                segment[i] == pattern[i % cycle_len]
                for i in range(len(segment))
            )
            if is_cycle:
                return True
        return False

    def _escalate_action(self) -> LoopAction:
        """Determine the action based on consecutive hits (from agent-loop-guard)."""
        hits = self._consecutive_hits
        cfg = self.action_config
        if hits >= cfg.escalate_threshold:
            return LoopAction.ESCALATE
        if hits >= cfg.stop_threshold:
            return LoopAction.STOP
        if hits >= cfg.warn_threshold:
            return LoopAction.WARN
        return LoopAction.CONTINUE

    def is_looping(self, tool: str, args: dict[str, Any]) -> bool:
        """Check if recording this action would trigger a loop.

        Does NOT record the action — call ``record`` after a successful
        action, or call ``check_and_record`` to do both atomically.
        """
        h = _action_hash(tool, args)
        with self._lock:
            if self._count_in_window(h) >= self.threshold - 1:
                return True
            if self._detect_fuzzy(tool, args) is not None:
                return True
            return bool(self._detect_cycle(tool, args))

    def check_and_record(self, tool: str, args: dict[str, Any]) -> LoopHit | None:
        """Atomically check + record. Returns LoopHit if blocked, None if ok.

        Blocked actions are NOT appended to history so they don't inflate
        future counts; LoopHit.action is preserved for callers to escalate.
        """
        h = _action_hash(tool, args)
        with self._lock:
            hit = self._detect_any_loop(tool, args, h)
            if hit is not None:
                # Preserve action escalation for callers; do not pollute history.
                return hit
            self._history.append(h)
            self._tool_history.append((tool, args))
            self._consecutive_hits = 0
            return None

    def _detect_any_loop(self, tool: str, args: dict[str, Any], h: str) -> LoopHit | None:
        """Try all detection methods. Returns LoopHit or None."""
        hit = self._detect_exact(tool, args, h)
        if hit is None:
            hit = self._detect_fuzzy_hit(tool, args, h)
        if hit is None:
            hit = self._detect_cycle_hit(tool, args, h)
        return hit

    def _detect_exact(self, tool: str, args: dict[str, Any], h: str) -> LoopHit | None:
        """Exact repeat detection."""
        current = self._count_in_window(h)
        if current < self.threshold - 1:
            return None
        self._consecutive_hits += 1
        self._blocks += 1
        return LoopHit(tool=tool, args=args, hash_value=h, repeat_count=current + 1,
                       window=self.window, detection="exact", similarity=1.0,
                       action=self._escalate_action(), consecutive_hits=self._consecutive_hits)

    def _detect_fuzzy_hit(self, tool: str, args: dict[str, Any], h: str) -> LoopHit | None:
        """Fuzzy repeat detection."""
        fuzzy_result = self._detect_fuzzy(tool, args)
        if fuzzy_result is None:
            return None
        sim, _ = fuzzy_result
        self._consecutive_hits += 1
        self._blocks += 1
        return LoopHit(tool=tool, args=args, hash_value=h, repeat_count=2,
                       window=self.window, detection="fuzzy", similarity=sim,
                       action=self._escalate_action(), consecutive_hits=self._consecutive_hits)

    def _detect_cycle_hit(self, tool: str, args: dict[str, Any], h: str) -> LoopHit | None:
        """Cycle detection."""
        if not self._detect_cycle(tool, args):
            return None
        self._consecutive_hits += 1
        self._blocks += 1
        return LoopHit(tool=tool, args=args, hash_value=h, repeat_count=self.cycle_min_repeats,
                       window=self.window, detection="cycle", similarity=0.0,
                       action=self._escalate_action(), consecutive_hits=self._consecutive_hits)

    def record(self, tool: str, args: dict[str, Any]) -> None:
        """Record an action without checking. Useful for seeding history."""
        h = _action_hash(tool, args)
        with self._lock:
            self._history.append(h)
            self._tool_history.append((tool, args))

    def reset(self) -> None:
        """Clear history (e.g. on new session)."""
        with self._lock:
            self._history.clear()
            self._tool_history.clear()
            self._consecutive_hits = 0
            self._blocks = 0

    @property
    def blocks(self) -> int:
        """Total number of loop blocks since creation."""
        return self._blocks

    @property
    def size(self) -> int:
        """Current history size."""
        return len(self._history)

    def stats(self) -> dict[str, Any]:
        """Return a stats dict for observability."""
        with self._lock:
            return {
                "window": self.window,
                "threshold": self.threshold,
                "fuzzy_threshold": self.fuzzy_threshold,
                "fuzzy_enabled": self.fuzzy_enabled,
                "cycle_enabled": self.cycle_enabled,
                "size": len(self._history),
                "blocks": self._blocks,
                "consecutive_hits": self._consecutive_hits,
                "unique_hashes": len(set(self._history)),
            }
