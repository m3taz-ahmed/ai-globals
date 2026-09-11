#!/usr/bin/env python3
"""Semantic circuit breaker for agent operations.

Inspired by agentsre + ballast: opens on *semantic validation failure rate*,
not HTTP errors. A semantic failure means the agent's output failed a
quality/validation check (e.g. output gate, plan diff validator, guardrail),
not a transport-level error.

This protects downstream consumers from a degraded agent that is
repeatedly producing invalid outputs. When the breaker opens, callers
should fall back to a different model, retry with stricter constraints,
or surface the issue to a human.

Architecture::

    agent output -> validation -> SemanticCircuitBreaker.record_success/failure
                                -> if failure_rate > threshold: OPEN
                                -> after open_timeout: HALF_OPEN (probe)
                                -> if probe succeeds: CLOSED
                                -> if probe fails: OPEN (reset timer)

Usage::

    from runtime.agent_circuit_breaker import SemanticCircuitBreaker, CbConfig

    cb = SemanticCircuitBreaker()
    if not cb.can_execute():
        raise AizeeError("CIRCUIT_OPEN", "agent circuit breaker is open")

    try:
        result = agent.run(prompt)
        if validate(result):
            cb.record_success()
        else:
            cb.record_failure()
    except Exception:
        cb.record_failure()
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

from runtime.schemas import AizeeError, ErrorSeverity

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class CbState(str, Enum):
    """Circuit breaker states (standard pattern).

    - CLOSED: calls flow normally; failure rate is monitored.
    - OPEN: all calls are blocked; waiting for the open_timeout to elapse.
    - HALF_OPEN: limited probe calls are allowed to test recovery.
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


@dataclass
class CbConfig:
    """Configuration for the semantic circuit breaker.

    Attributes:
        failure_threshold: Failure rate (0.0-1.0) that trips the breaker to OPEN.
        success_threshold: Success rate (0.0-1.0) required in HALF_OPEN to close.
        min_calls: Minimum number of calls before the failure rate is evaluated.
        open_timeout: Seconds the breaker stays OPEN before transitioning to HALF_OPEN.
        half_open_max_calls: Max probe calls allowed in HALF_OPEN state.
    """

    failure_threshold: float = 0.15
    success_threshold: float = 0.95
    min_calls: int = 20
    open_timeout: float = 60.0
    half_open_max_calls: int = 5

    def __post_init__(self) -> None:
        if not 0.0 < self.failure_threshold < 1.0:
            raise ValueError("failure_threshold must be in (0, 1)")
        if not 0.0 < self.success_threshold <= 1.0:
            raise ValueError("success_threshold must be in (0, 1]")
        if self.min_calls < 1:
            raise ValueError("min_calls must be >= 1")
        if self.open_timeout <= 0:
            raise ValueError("open_timeout must be > 0")
        if self.half_open_max_calls < 1:
            raise ValueError("half_open_max_calls must be >= 1")


class CircuitBreakerError(AizeeError):
    """Raised when the circuit breaker blocks an operation."""

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        super().__init__("CIRCUIT_OPEN", message, ErrorSeverity.HIGH, context)


# ---------------------------------------------------------------------------
# Callback type
# ---------------------------------------------------------------------------

StateChangeCallback = Callable[[CbState, CbState], None]


# ---------------------------------------------------------------------------
# Circuit breaker
# ---------------------------------------------------------------------------


class SemanticCircuitBreaker:
    """Semantic circuit breaker that tracks validation failure rates.

    Unlike a traditional HTTP circuit breaker, this opens when the agent's
    *outputs* fail semantic validation (quality checks, guardrails, etc.),
    not when the transport fails. This catches a degraded-but-responsive
    agent that is producing garbage.

    Thread-safe via ``RLock``. State transitions fire registered callbacks
    so callers can log, alert, or trigger fallback logic.
    """

    def __init__(self, config: CbConfig | None = None) -> None:
        self._config = config or CbConfig()
        self._lock = threading.RLock()
        self._state: CbState = CbState.CLOSED
        self._total = 0
        self._successes = 0
        self._failures = 0
        self._opened_at: float | None = None
        self._half_open_calls = 0
        self._half_open_successes = 0
        self._half_open_failures = 0
        self._callbacks: list[StateChangeCallback] = []

    # -- Public API ----------------------------------------------------------

    def record_success(self) -> None:
        """Record a successful (semantically valid) agent operation."""
        with self._lock:
            if self._state is CbState.HALF_OPEN:
                self._half_open_successes += 1
                self._half_open_calls += 1
                self._maybe_close()
            else:
                self._successes += 1
                self._total += 1
                self._maybe_open_from_closed()

    def record_failure(self) -> None:
        """Record a failed (semantically invalid) agent operation."""
        with self._lock:
            if self._state is CbState.HALF_OPEN:
                self._half_open_failures += 1
                self._half_open_calls += 1
                self._trip_open()
            else:
                self._failures += 1
                self._total += 1
                self._maybe_open_from_closed()

    def can_execute(self) -> bool:
        """Check if a call is allowed under the current breaker state."""
        with self._lock:
            if self._state is CbState.CLOSED:
                return True
            if self._state is CbState.OPEN:
                if self._should_half_open():
                    self._transition(CbState.HALF_OPEN)
                    self._half_open_calls = 0
                    self._half_open_successes = 0
                    self._half_open_failures = 0
                    return True
                return False
            # HALF_OPEN: allow limited probe calls
            return self._half_open_calls < self._config.half_open_max_calls

    def state(self) -> CbState:
        """Return the current breaker state."""
        with self._lock:
            return self._state

    def stats(self) -> dict[str, Any]:
        """Return current statistics for monitoring."""
        with self._lock:
            total = self._total
            failure_rate = self._failures / total if total > 0 else 0.0
            return {
                "state": self._state.value,
                "total": total,
                "success": self._successes,
                "failure": self._failures,
                "failure_rate": round(failure_rate, 4),
                "opened_at": self._opened_at,
                "half_open_calls": self._half_open_calls,
                "half_open_successes": self._half_open_successes,
                "half_open_failures": self._half_open_failures,
            }

    def reset(self) -> None:
        """Reset the breaker to CLOSED with zeroed counters."""
        with self._lock:
            prev = self._state
            self._state = CbState.CLOSED
            self._total = 0
            self._successes = 0
            self._failures = 0
            self._opened_at = None
            self._half_open_calls = 0
            self._half_open_successes = 0
            self._half_open_failures = 0
        if prev is not CbState.CLOSED:
            self._fire_callbacks(prev, CbState.CLOSED)
        _logger.info("circuit breaker reset to CLOSED")

    def on_state_change(self, callback: StateChangeCallback) -> None:
        """Register a callback invoked on state transitions.

        The callback receives ``(old_state, new_state)``.
        """
        with self._lock:
            self._callbacks.append(callback)

    # -- Internal helpers (each < 30 lines) ---------------------------------

    def _maybe_open_from_closed(self) -> None:
        """Check if the failure rate in CLOSED state warrants opening."""
        if self._total < self._config.min_calls:
            return
        rate = self._failures / self._total
        if rate >= self._config.failure_threshold:
            self._trip_open()

    def _trip_open(self) -> None:
        """Transition to OPEN state and reset half-open counters."""
        prev = self._state
        self._state = CbState.OPEN
        self._opened_at = time.monotonic()
        self._half_open_calls = 0
        self._half_open_successes = 0
        self._half_open_failures = 0
        _logger.warning(
            "circuit breaker tripped OPEN (failures=%d/%d, rate=%.2f)",
            self._failures,
            self._total,
            self._failures / self._total if self._total else 0.0,
        )
        self._fire_callbacks(prev, CbState.OPEN)

    def _maybe_close(self) -> None:
        """Check if HALF_OPEN probe results warrant closing."""
        if self._half_open_calls < self._config.half_open_max_calls:
            return
        total_ho = self._half_open_calls
        success_rate = self._half_open_successes / total_ho if total_ho > 0 else 0.0
        if success_rate >= self._config.success_threshold:
            self._transition(CbState.CLOSED)
            self._total = 0
            self._successes = 0
            self._failures = 0
            self._opened_at = None
        else:
            self._trip_open()

    def _should_half_open(self) -> bool:
        """Check if enough time has elapsed to attempt HALF_OPEN."""
        if self._opened_at is None:
            return False
        elapsed = time.monotonic() - self._opened_at
        return elapsed >= self._config.open_timeout

    def _transition(self, new_state: CbState) -> None:
        """Transition to a new state and fire callbacks."""
        prev = self._state
        if prev is new_state:
            return
        self._state = new_state
        _logger.info("circuit breaker transitioned %s -> %s", prev.value, new_state.value)
        self._fire_callbacks(prev, new_state)

    def _fire_callbacks(self, old: CbState, new: CbState) -> None:
        """Invoke all registered state-change callbacks outside the lock."""
        callbacks = list(self._callbacks)
        for cb in callbacks:
            try:
                cb(old, new)
            except Exception:
                _logger.exception("state-change callback failed")
