#!/usr/bin/env python3
"""Learning loop: record-consolidate-rank-inject (WS-G).

LEARN-01: Hook bindings — bind learning hooks to the HookLifecycle to
automatically record action outcomes (success/failure) without manual
calls.

LEARN-02: Record-consolidate-rank-inject — the four-stage learning loop:
1. **Record**: Capture action outcomes (action, result, success, timestamp).
2. **Consolidate**: Merge duplicate/similar outcomes into patterns.
3. **Rank**: Score patterns by success rate and frequency.
4. **Inject**: Feed top-ranked patterns back into the prompt as context.

Inspired by Reflexion (arXiv 2303.11366) — self-reflection from past
trials — and mem0's consolidation pattern.

Usage::

    from runtime.learning_loop import LearningLoop
    loop = LearningLoop()
    loop.bind_to_hooks(registry)  # LEARN-01: auto-record
    loop.record("exec", {"ok": True, "gate": "probity"})
    loop.record("exec", {"ok": True, "gate": "probity"})
    loop.record("exec", {"ok": False, "gate": "probity"})
    patterns = loop.consolidate()
    ranked = loop.rank(patterns)
    context = loop.inject(ranked, top_k=3)
    # context is now injected into the prompt
"""

from __future__ import annotations

import json
import logging
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runtime.hook_lifecycle import HookContext, HookPhase, HookRegistry

logger = logging.getLogger(__name__)

_SENSITIVE_KEYS = {"password", "secret", "token", "api_key", "apikey", "auth", "credential"}


def _redact_result(result: dict[str, Any]) -> dict[str, Any]:
    """Drop sensitive keys before persisting learning outcomes."""
    return {k: v for k, v in result.items() if k.lower() not in _SENSITIVE_KEYS}


def _parse_ts(value: str) -> datetime:
    """Parse ISO-8601 timestamp; fall back to epoch on garbage."""
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return datetime.fromtimestamp(0, tz=timezone.utc)


def _coerce_ok(value: Any) -> bool:
    """Explicit bool coercion: the string "false" is falsy, not truthy."""
    if isinstance(value, str):
        return value.strip().lower() not in ("", "false", "0", "no", "off", "none", "null")
    return bool(value)


@dataclass
class Outcome:
    """A single action outcome record.

    Attributes:
        action: Action type (e.g. "exec", "Read", "Write").
        result: The kernel response dict.
        success: Whether the action succeeded (result["ok"] is True).
        gate: Which gate made the decision (if any).
        timestamp: ISO-8601 timestamp of the record.
        session_id: Optional session identifier for grouping.
    """

    action: str
    result: dict[str, Any] = field(default_factory=dict)
    success: bool = False
    gate: str = ""
    timestamp: str = ""
    session_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "result": self.result,
            "success": self.success,
            "gate": self.gate,
            "timestamp": self.timestamp,
            "session_id": self.session_id,
        }


@dataclass
class Pattern:
    """A consolidated pattern from multiple outcomes.

    Attributes:
        action: Action type this pattern covers.
        gate: Gate that typically handles this action.
        total: Total number of outcomes consolidated.
        successes: Number of successful outcomes.
        failures: Number of failed outcomes.
        success_rate: successes / total (0.0-1.0).
        last_seen: Timestamp of the most recent outcome.
    """

    action: str
    gate: str
    total: int = 0
    successes: int = 0
    failures: int = 0
    success_rate: float = 0.0
    last_seen: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "gate": self.gate,
            "total": self.total,
            "successes": self.successes,
            "failures": self.failures,
            "success_rate": round(self.success_rate, 4),
            "last_seen": self.last_seen,
        }


class LearningLoop:
    """Record-consolidate-rank-inject learning loop (WS-G).

    LEARN-01: Can bind to a HookRegistry to auto-record outcomes.
    LEARN-02: Implements the four-stage loop.
    """

    def __init__(self, persist_path: Path | None = None) -> None:
        self._outcomes: deque[Outcome] = deque(maxlen=10000)
        self._persist_path = persist_path
        self._lock = threading.RLock()
        self._dirty = False
        self._persist_counter = 0
        self._persist_batch_size = 100  # persist every 100 records
        self._load()

    # --- LEARN-01: Hook bindings -----------------------------------------

    def bind_to_hooks(self, registry: HookRegistry) -> None:
        """LEARN-01: Bind learning hooks to the HookLifecycle.

        Registers a POST_RESPONSE hook that auto-records action outcomes.
        Also registers an ON_ERROR hook to record failures.
        """
        def record_outcome(ctx: HookContext) -> None:
            result = ctx.results.get("response", {})
            if not isinstance(result, dict):
                logger.debug("learning_loop: skipping non-dict result for %s", ctx.action)
                return
            self.record(
                action=ctx.action,
                result=result,
                success=_coerce_ok(result.get("ok", False)),
                gate=str(result.get("gate", "")),
            )

        def record_error(ctx: HookContext) -> None:
            if ctx.errors:
                self.record(
                    action=ctx.action,
                    result={},
                    success=False,
                    gate="error",
                )

        registry.register(HookPhase.POST_RESPONSE, record_outcome)
        registry.register(HookPhase.ON_ERROR, record_error)

    # --- LEARN-02: Record ------------------------------------------------

    def record(
        self,
        action: str,
        result: dict[str, Any] | None = None,
        success: bool = False,
        gate: str = "",
        session_id: str = "",
    ) -> Outcome:
        """LEARN-02 Stage 1: Record an action outcome."""
        if result is not None and not isinstance(result, dict):
            logger.warning("learning_loop.record: result must be dict, got %s; skipping", type(result).__name__)
            raise TypeError(f"result must be dict or None, got {type(result).__name__}")
        outcome = Outcome(
            action=action,
            result=_redact_result(result or {}),
            success=success,
            gate=gate,
            timestamp=datetime.now(timezone.utc).isoformat(),
            session_id=session_id,
        )
        with self._lock:
            self._outcomes.append(outcome)
            self._dirty = True
            # Batch persist: only write to disk every ``_persist_batch_size``
            # records or when the deque is full, to avoid O(n) disk I/O on
            # every record() call.
            self._persist_counter += 1
            if self._persist_counter >= self._persist_batch_size:
                self._persist()
                self._persist_counter = 0
        return outcome

    # --- LEARN-02: Consolidate -------------------------------------------

    def consolidate(self) -> list[Pattern]:
        """LEARN-02 Stage 2: Consolidate outcomes into patterns.

        Groups outcomes by (action, gate) and computes aggregate stats.
        """
        groups: dict[tuple[str, str], list[Outcome]] = defaultdict(list)
        for o in self._outcomes:
            groups[(o.action, o.gate)].append(o)
        patterns: list[Pattern] = []
        for (action, gate), outcomes in groups.items():
            total = len(outcomes)
            successes = sum(1 for o in outcomes if o.success)
            failures = total - successes
            # ISO timestamps: parse, don't lexicographic-max.
            last_seen = max(_parse_ts(o.timestamp) for o in outcomes).isoformat() if outcomes else ""
            patterns.append(Pattern(
                action=action,
                gate=gate,
                total=total,
                successes=successes,
                failures=failures,
                success_rate=successes / total if total > 0 else 0.0,
                last_seen=last_seen,
            ))
        # Flush any dirty state when consolidating.
        with self._lock:
            if self._dirty:
                self._persist()
                self._persist_counter = 0
        return patterns

    # --- LEARN-02: Rank --------------------------------------------------

    def rank(self, patterns: list[Pattern] | None = None) -> list[Pattern]:
        """LEARN-02 Stage 3: Rank patterns by significance.

        Sorts by: (1) total frequency (more data = more confidence),
        (2) success rate (higher = better pattern), (3) recency.
        """
        if patterns is None:
            patterns = self.consolidate()
        return sorted(
            patterns,
            key=lambda p: (p.total, p.success_rate, p.last_seen),
            reverse=True,
        )

    # --- LEARN-02: Inject ------------------------------------------------

    def inject(self, ranked: list[Pattern] | None = None, top_k: int = 5) -> str:
        """LEARN-02 Stage 4: Inject top patterns as prompt context.

        Returns a formatted string suitable for inclusion in the system
        prompt. Only includes patterns with at least 2 observations.
        """
        if ranked is None:
            ranked = self.rank()
        significant = [p for p in ranked if p.total >= 2][:top_k]
        if not significant:
            return ""
        lines = ["## Learned Patterns (from past actions)"]
        for p in significant:
            status = "reliable" if p.success_rate >= 0.8 else "unreliable"
            lines.append(
                f"- {p.action} (gate: {p.gate}): "
                f"{p.successes}/{p.total} success ({p.success_rate:.0%}) — {status}"
            )
        return "\n".join(lines)

    # --- Utilities -------------------------------------------------------

    @property
    def outcome_count(self) -> int:
        """Total number of recorded outcomes."""
        return len(self._outcomes)

    def flush(self) -> None:
        """Force-persist any dirty outcomes to disk immediately."""
        with self._lock:
            if self._dirty:
                self._persist()
                self._persist_counter = 0

    def clear(self) -> None:
        """Clear all recorded outcomes."""
        with self._lock:
            self._outcomes.clear()
            self._persist()

    def _persist(self) -> None:
        """Persist outcomes to disk if a path is configured."""
        if self._persist_path is None:
            return
        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            data = [o.to_dict() for o in self._outcomes]
            self._persist_path.write_text(
                json.dumps(data, indent=2), encoding="utf-8",
            )
        except OSError as exc:
            logger.warning("Failed to persist learning outcomes: %s", exc)

    def _load(self) -> None:
        """Load previously persisted outcomes from disk."""
        if self._persist_path is None or not self._persist_path.exists():
            return
        try:
            data = json.loads(self._persist_path.read_text(encoding="utf-8"))
            for item in data:
                self._outcomes.append(Outcome(
                    action=item.get("action", ""),
                    result=item.get("result", {}),
                    success=item.get("success", False),
                    gate=item.get("gate", ""),
                    timestamp=item.get("timestamp", ""),
                    session_id=item.get("session_id", ""),
                ))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load learning outcomes: %s", exc)
