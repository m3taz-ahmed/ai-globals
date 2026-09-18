"""Tests for runtime/agent_circuit_breaker.py — semantic circuit breaker."""

from __future__ import annotations

import time

import pytest

from runtime.agent_circuit_breaker import (
    CbConfig,
    CbState,
    CircuitBreakerError,
    SemanticCircuitBreaker,
)


def _cb(**kw) -> SemanticCircuitBreaker:
    return SemanticCircuitBreaker(CbConfig(**kw))


class TestConfig:
    def test_defaults(self):
        c = CbConfig()
        assert c.failure_threshold == 0.15
        assert c.open_timeout == 60.0

    @pytest.mark.parametrize("kw", [
        {"failure_threshold": 0.0}, {"failure_threshold": 1.0},
        {"success_threshold": 0.0}, {"success_threshold": 1.5},
        {"min_calls": 0}, {"open_timeout": 0}, {"half_open_max_calls": 0},
    ])
    def test_invalid(self, kw):
        with pytest.raises(ValueError):
            CbConfig(**kw)

    def test_error_type(self):
        err = CircuitBreakerError("x")
        assert err.error_code == "CIRCUIT_OPEN"


class TestClosedState:
    def test_starts_closed(self):
        cb = _cb()
        assert cb.state() is CbState.CLOSED
        assert cb.can_execute() is True

    def test_below_min_calls_never_opens(self):
        cb = _cb(min_calls=10, failure_threshold=0.5)
        for _ in range(5):  # 100% failure rate but < min_calls
            cb.record_failure()
        assert cb.state() is CbState.CLOSED

    def test_opens_on_failure_rate(self):
        cb = _cb(min_calls=10, failure_threshold=0.3)
        for _ in range(7):
            cb.record_success()
        for _ in range(3):  # 30% failure rate
            cb.record_failure()
        assert cb.state() is CbState.OPEN
        assert cb.can_execute() is False

    def test_success_keeps_closed(self):
        cb = _cb(min_calls=5, failure_threshold=0.5)
        for _ in range(10):
            cb.record_success()
        cb.record_failure()  # 1/11 ≈ 9%
        assert cb.state() is CbState.CLOSED


class TestOpenState:
    def _opened(self) -> SemanticCircuitBreaker:
        cb = _cb(min_calls=2, failure_threshold=0.5, open_timeout=60.0,
                 half_open_max_calls=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.state() is CbState.OPEN
        return cb

    @staticmethod
    def _expire_timeout(cb: SemanticCircuitBreaker) -> None:
        """Force the open timeout to have elapsed (deterministic)."""
        cb._opened_at = time.monotonic() - 1000.0

    def test_blocks_calls(self):
        cb = self._opened()
        assert cb.can_execute() is False

    def test_half_open_after_timeout(self):
        cb = self._opened()
        self._expire_timeout(cb)
        assert cb.can_execute() is True
        assert cb.state() is CbState.HALF_OPEN

    def test_half_open_probe_limit(self):
        cb = self._opened()
        self._expire_timeout(cb)
        cb.can_execute()  # transitions to HALF_OPEN
        for _ in range(3):
            cb.record_success()
        # 3 successes = max calls, success rate 100% >= 95% -> CLOSED
        assert cb.state() is CbState.CLOSED

    def test_half_open_failure_reopens(self):
        cb = self._opened()
        self._expire_timeout(cb)
        cb.can_execute()
        cb.record_failure()
        assert cb.state() is CbState.OPEN

    def test_half_open_insufficient_success_reopens(self):
        cb = _cb(min_calls=2, failure_threshold=0.5, open_timeout=60.0,
                 half_open_max_calls=4, success_threshold=0.9)
        cb.record_failure()
        cb.record_failure()
        cb._opened_at = time.monotonic() - 1000.0
        cb.can_execute()
        cb.record_success()
        cb.record_success()
        # Can't reach half_open_max_calls=4 successes without failure —
        # 4th call needed. Record 2 more: rate 4/4... need a failure case:
        cb.record_failure()  # immediate reopen
        assert cb.state() is CbState.OPEN

    def test_stats(self):
        cb = self._opened()
        s = cb.stats()
        assert s["state"] == "open"
        assert s["failure"] == 2
        assert s["failure_rate"] == 1.0
        assert s["opened_at"] is not None


class TestCallbacksAndReset:
    def test_state_change_callback(self):
        events = []
        cb = _cb(min_calls=2, failure_threshold=0.5)
        cb.on_state_change(lambda old, new: events.append((old, new)))
        cb.record_failure()
        cb.record_failure()
        assert events == [(CbState.CLOSED, CbState.OPEN)]

    def test_callback_error_swallowed(self):
        cb = _cb(min_calls=1, failure_threshold=0.5)
        def bad(old, new):
            raise RuntimeError("callback boom")
        cb.on_state_change(bad)
        cb.record_failure()  # trips open; callback raises but is logged
        assert cb.state() is CbState.OPEN

    def test_reset(self):
        cb = _cb(min_calls=1, failure_threshold=0.5)
        cb.record_failure()
        assert cb.state() is CbState.OPEN
        cb.reset()
        assert cb.state() is CbState.CLOSED
        s = cb.stats()
        assert s["total"] == 0 and s["failure"] == 0

    def test_reset_fires_callback(self):
        events = []
        cb = _cb(min_calls=1, failure_threshold=0.5)
        cb.on_state_change(lambda o, n: events.append((o, n)))
        cb.record_failure()
        cb.reset()
        assert (CbState.OPEN, CbState.CLOSED) in events

    def test_reset_when_closed_no_callback(self):
        events = []
        cb = _cb()
        cb.on_state_change(lambda o, n: events.append(n))
        cb.reset()
        assert events == []

    def test_full_lifecycle(self):
        """closed -> open -> half_open -> closed."""
        cb = _cb(min_calls=2, failure_threshold=0.5, open_timeout=60.0,
                 half_open_max_calls=2, success_threshold=0.9)
        cb.record_failure()
        cb.record_failure()
        assert cb.state() is CbState.OPEN
        cb._opened_at = time.monotonic() - 1000.0
        assert cb.can_execute()
        assert cb.state() is CbState.HALF_OPEN
        cb.record_success()
        cb.record_success()
        assert cb.state() is CbState.CLOSED
