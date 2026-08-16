#!/usr/bin/env python3
"""Budget rate limiting with leaky bucket (from agent-governance-toolkit).

Per-agent rate limiting with configurable burst and sustained rates.
Prevents budget exhaustion from runaway agents.

Usage::

    from runtime.rate_limiter import RateLimiter

    limiter = RateLimiter(max_burst=10, refill_per_second=2.0)
    if limiter.allow("agent-1"):
        # proceed
        pass
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class TokenBucket:
    """Leaky bucket token bucket for rate limiting."""

    capacity: float
    refill_rate: float  # tokens per second
    tokens: float = 0.0
    last_refill: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        if self.tokens == 0.0:
            self.tokens = self.capacity

    def _refill(self) -> None:
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

    def try_consume(self, tokens: float = 1.0) -> bool:
        """Try to consume tokens. Returns True if allowed."""
        self._refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def available(self) -> float:
        """Return available tokens (after refill)."""
        self._refill()
        return self.tokens


@dataclass
class RateLimiter:
    """Per-agent rate limiter using token buckets.

    Each agent gets its own bucket. Prevents budget exhaustion from
    runaway agents while allowing bursty traffic.
    """

    max_burst: float = 10.0
    refill_per_second: float = 2.0
    _buckets: dict[str, TokenBucket] = field(default_factory=dict)

    def _get_bucket(self, agent_id: str) -> TokenBucket:
        if agent_id not in self._buckets:
            self._buckets[agent_id] = TokenBucket(
                capacity=self.max_burst,
                refill_rate=self.refill_per_second,
            )
        return self._buckets[agent_id]

    def allow(self, agent_id: str, tokens: float = 1.0) -> bool:
        """Check if agent is allowed to proceed."""
        return self._get_bucket(agent_id).try_consume(tokens)

    def available(self, agent_id: str) -> float:
        """Return available tokens for an agent."""
        return self._get_bucket(agent_id).available()

    def reset(self, agent_id: str) -> None:
        """Reset an agent's bucket."""
        if agent_id in self._buckets:
            del self._buckets[agent_id]


if __name__ == "__main__":
    limiter = RateLimiter(max_burst=5, refill_per_second=1.0)
    for i in range(7):
        print(f"Request {i}: {'allowed' if limiter.allow('a1') else 'denied'}")
