#!/usr/bin/env python3
"""Policy decision caching (from agent-policy-engine).

Caches PDP decisions to avoid redundant evaluation. Cache entries
expire after a configurable TTL. Invalidated on policy changes.

Usage::

    from runtime.policy_cache import PolicyDecisionCache

    cache = PolicyDecisionCache(ttl_seconds=300)
    cache.put("key-1", decision)
    cached = cache.get("key-1")
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CacheEntry:
    """A cached policy decision."""

    key: str
    value: Any
    expires_at: float

    @property
    def expired(self) -> bool:
        return time.time() > self.expires_at


@dataclass
class PolicyDecisionCache:
    """Cache for policy decisions with TTL (from agent-policy-engine).

    Reduces PDP load by caching recent decisions. Cache is invalidated
    on policy changes or when TTL expires.
    """

    ttl_seconds: int = 300
    max_entries: int = 10000
    _cache: dict[str, CacheEntry] = field(default_factory=dict)

    @staticmethod
    def make_key(
        subject_id: str,
        operation_id: str,
        target_id: str,
        arguments_hash: str = "",
    ) -> str:
        """Create a cache key from decision parameters."""
        raw = f"{subject_id}:{operation_id}:{target_id}:{arguments_hash}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def put(self, key: str, value: Any) -> None:
        """Add or update a cache entry."""
        if len(self._cache) >= self.max_entries:
            self._evict_oldest()
        self._cache[key] = CacheEntry(
            key=key, value=value,
            expires_at=time.time() + self.ttl_seconds,
        )

    def get(self, key: str) -> Any | None:
        """Get a cached value. Returns None if expired or missing."""
        entry = self._cache.get(key)
        if entry is None or entry.expired:
            if entry and entry.expired:
                del self._cache[key]
            return None
        return entry.value

    def invalidate(self, key: str) -> None:
        """Invalidate a specific cache entry."""
        self._cache.pop(key, None)

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()

    def cleanup_expired(self) -> int:
        """Remove all expired entries. Returns count removed."""
        now = time.time()
        expired = [k for k, e in self._cache.items() if now > e.expires_at]
        for k in expired:
            del self._cache[k]
        return len(expired)

    def _evict_oldest(self) -> None:
        """Evict the entry with earliest expiry."""
        if not self._cache:
            return
        oldest_key = min(self._cache, key=lambda k: self._cache[k].expires_at)
        del self._cache[oldest_key]

    @property
    def size(self) -> int:
        return len(self._cache)


if __name__ == "__main__":
    cache = PolicyDecisionCache(ttl_seconds=1)
    key = cache.make_key("u1", "read", "doc1")
    cache.put(key, {"decision": "allow"})
    print(f"Cached: {cache.get(key)}")
