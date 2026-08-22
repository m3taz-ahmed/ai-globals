"""Tests for runtime/policy_cache.py."""

from __future__ import annotations

import time

from runtime.policy_cache import CacheEntry, PolicyDecisionCache


class TestCacheEntry:
    def test_expired_returns_false_before_expiry(self) -> None:
        # Arrange
        entry = CacheEntry(key="k1", value="v1", expires_at=time.time() + 100)

        # Act & Assert
        assert entry.expired is False

    def test_expired_returns_true_after_expiry(self) -> None:
        # Arrange
        entry = CacheEntry(key="k1", value="v1", expires_at=time.time() - 1)

        # Act & Assert
        assert entry.expired is True

    def test_entry_stores_key_and_value(self) -> None:
        # Arrange & Act
        entry = CacheEntry(key="my-key", value={"decision": "allow"}, expires_at=9999.0)

        # Assert
        assert entry.key == "my-key"
        assert entry.value == {"decision": "allow"}


class TestPolicyDecisionCacheMakeKey:
    def test_make_key_returns_hex_string(self) -> None:
        # Act
        key = PolicyDecisionCache.make_key("user1", "read", "doc1")

        # Assert
        assert isinstance(key, str)
        assert len(key) == 16

    def test_make_key_deterministic(self) -> None:
        # Act
        key1 = PolicyDecisionCache.make_key("user1", "read", "doc1")
        key2 = PolicyDecisionCache.make_key("user1", "read", "doc1")

        # Assert
        assert key1 == key2

    def test_make_key_differs_with_different_params(self) -> None:
        # Act
        key1 = PolicyDecisionCache.make_key("user1", "read", "doc1")
        key2 = PolicyDecisionCache.make_key("user2", "read", "doc1")

        # Assert
        assert key1 != key2

    def test_make_key_includes_arguments_hash(self) -> None:
        # Act
        key1 = PolicyDecisionCache.make_key("u1", "read", "d1", "hash_a")
        key2 = PolicyDecisionCache.make_key("u1", "read", "d1", "hash_b")

        # Assert
        assert key1 != key2


class TestPolicyDecisionCachePutGet:
    def test_put_then_get_returns_value(self) -> None:
        # Arrange
        cache = PolicyDecisionCache(ttl_seconds=300)

        # Act
        cache.put("key1", {"decision": "allow"})

        # Assert
        assert cache.get("key1") == {"decision": "allow"}

    def test_get_missing_key_returns_none(self) -> None:
        # Arrange
        cache = PolicyDecisionCache()

        # Act
        result = cache.get("nonexistent")

        # Assert
        assert result is None

    def test_put_overwrites_existing_value(self) -> None:
        # Arrange
        cache = PolicyDecisionCache(ttl_seconds=300)
        cache.put("key1", "old")

        # Act
        cache.put("key1", "new")

        # Assert
        assert cache.get("key1") == "new"


class TestPolicyDecisionCacheExpiration:
    def test_get_expired_entry_returns_none(self) -> None:
        # Arrange
        cache = PolicyDecisionCache(ttl_seconds=1)
        cache.put("key1", "value1")

        # Act — simulate expiry by manipulating the entry
        cache._cache["key1"].expires_at = time.time() - 1
        result = cache.get("key1")

        # Assert
        assert result is None

    def test_get_expired_entry_removes_from_cache(self) -> None:
        # Arrange
        cache = PolicyDecisionCache(ttl_seconds=1)
        cache.put("key1", "value1")
        cache._cache["key1"].expires_at = time.time() - 1

        # Act
        cache.get("key1")

        # Assert
        assert "key1" not in cache._cache

    def test_cleanup_expired_removes_expired_entries(self) -> None:
        # Arrange
        cache = PolicyDecisionCache(ttl_seconds=300)
        cache.put("key1", "v1")
        cache.put("key2", "v2")
        cache._cache["key1"].expires_at = time.time() - 1

        # Act
        removed = cache.cleanup_expired()

        # Assert
        assert removed == 1
        assert cache.get("key2") == "v2"

    def test_cleanup_expired_returns_zero_when_none_expired(self) -> None:
        # Arrange
        cache = PolicyDecisionCache(ttl_seconds=300)
        cache.put("key1", "v1")

        # Act
        removed = cache.cleanup_expired()

        # Assert
        assert removed == 0


class TestPolicyDecisionCacheInvalidation:
    def test_invalidate_removes_entry(self) -> None:
        # Arrange
        cache = PolicyDecisionCache(ttl_seconds=300)
        cache.put("key1", "v1")

        # Act
        cache.invalidate("key1")

        # Assert
        assert cache.get("key1") is None

    def test_invalidate_missing_key_does_not_raise(self) -> None:
        # Arrange
        cache = PolicyDecisionCache()

        # Act & Assert — should not raise
        cache.invalidate("nonexistent")

    def test_clear_removes_all_entries(self) -> None:
        # Arrange
        cache = PolicyDecisionCache(ttl_seconds=300)
        cache.put("key1", "v1")
        cache.put("key2", "v2")

        # Act
        cache.clear()

        # Assert
        assert cache.size == 0


class TestPolicyDecisionCacheSize:
    def test_size_reflects_number_of_entries(self) -> None:
        # Arrange
        cache = PolicyDecisionCache(ttl_seconds=300)

        # Act
        cache.put("key1", "v1")
        cache.put("key2", "v2")

        # Assert
        assert cache.size == 2

    def test_size_zero_on_empty_cache(self) -> None:
        # Arrange
        cache = PolicyDecisionCache()

        # Act & Assert
        assert cache.size == 0


class TestPolicyDecisionCacheEviction:
    def test_eviction_when_max_entries_reached(self) -> None:
        # Arrange
        cache = PolicyDecisionCache(ttl_seconds=300, max_entries=2)

        # Act
        cache.put("key1", "v1")
        cache.put("key2", "v2")
        cache.put("key3", "v3")  # triggers eviction

        # Assert
        assert cache.size == 2
        assert cache.get("key3") == "v3"
