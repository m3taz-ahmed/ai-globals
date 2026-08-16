"""Tests for runtime/rate_limiter.py — budget rate limiting."""

from __future__ import annotations

import time

from runtime.rate_limiter import RateLimiter, TokenBucket


class TestTokenBucket:
    def test_initial_tokens_equal_capacity(self) -> None:
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        assert bucket.available() == 10.0

    def test_consume_reduces_tokens(self) -> None:
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        assert bucket.try_consume(3) is True
        assert bucket.available() == 7.0

    def test_consume_more_than_available_fails(self) -> None:
        bucket = TokenBucket(capacity=5, refill_rate=1.0)
        assert bucket.try_consume(10) is False

    def test_refill_over_time(self) -> None:
        bucket = TokenBucket(capacity=10, refill_rate=100.0)
        bucket.try_consume(10)
        time.sleep(0.02)
        assert bucket.available() > 0


class TestRateLimiter:
    def test_allow_within_burst(self) -> None:
        limiter = RateLimiter(max_burst=5, refill_per_second=1.0)
        for _ in range(5):
            assert limiter.allow("a1") is True

    def test_deny_over_burst(self) -> None:
        limiter = RateLimiter(max_burst=3, refill_per_second=0.01)
        for _ in range(3):
            limiter.allow("a1")
        assert limiter.allow("a1") is False

    def test_separate_buckets_per_agent(self) -> None:
        limiter = RateLimiter(max_burst=2, refill_per_second=0.01)
        limiter.allow("a1")
        limiter.allow("a1")
        assert limiter.allow("a1") is False
        assert limiter.allow("a2") is True  # Different agent

    def test_reset_clears_bucket(self) -> None:
        limiter = RateLimiter(max_burst=2, refill_per_second=0.01)
        limiter.allow("a1")
        limiter.allow("a1")
        limiter.reset("a1")
        assert limiter.allow("a1") is True

    def test_refill_restores_tokens(self) -> None:
        limiter = RateLimiter(max_burst=2, refill_per_second=100.0)
        limiter.allow("a1")
        limiter.allow("a1")
        time.sleep(0.02)
        assert limiter.allow("a1") is True
