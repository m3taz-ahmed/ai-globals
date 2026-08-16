#!/usr/bin/env python3
"""SimHash for near-duplicate detection in memory entries.

64-bit SimHash with Hamming distance for fast deduplication before
embedding. Inspired by OpenMemory's HSG implementation.

Usage::

    from memory.simhash import SimHashIndex

    index = SimHashIndex()
    index.add("mem-1", "The quick brown fox")
    is_dup = index.is_duplicate("mem-2", "The quick brown fox")  # True
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any

_SIMHASH_BITS = 64


def _canonical_tokens(text: str) -> list[str]:
    """Extract canonical token set for SimHash computation."""
    return [t.lower() for t in re.findall(r"\w+", text) if len(t) > 1]


def _token_hash(token: str) -> int:
    """Compute a stable 64-bit hash for a token using MD5."""
    digest = hashlib.md5(token.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "little")


def compute_simhash(text: str) -> str:
    """Compute a 64-bit SimHash for the given text."""
    tokens = _canonical_tokens(text)
    if not tokens:
        return "0" * 16
    weights: list[int] = [0] * _SIMHASH_BITS
    for token in tokens:
        h = _token_hash(token)
        for i in range(_SIMHASH_BITS):
            bit = (h >> i) & 1
            weights[i] += 1 if bit else -1
    result = 0
    for i in range(_SIMHASH_BITS):
        if weights[i] > 0:
            result |= (1 << i)
    return f"{result:016x}"


def hamming_distance(h1: str, h2: str) -> int:
    """Compute Hamming distance between two hex SimHash strings."""
    v1 = int(h1, 16)
    v2 = int(h2, 16)
    return bin(v1 ^ v2).count("1")


@dataclass
class SimHashIndex:
    """Index of SimHash values for near-duplicate detection.

    Uses Hamming distance with a configurable threshold (default: 3 bits
    out of 64) to identify near-duplicates.
    """

    threshold: int = 3
    _entries: dict[str, str] = field(default_factory=dict)  # id → simhash

    def add(self, entry_id: str, text: str) -> str:
        """Add an entry and return its SimHash."""
        h = compute_simhash(text)
        self._entries[entry_id] = h
        return h

    def add_hash(self, entry_id: str, simhash: str) -> None:
        """Add a pre-computed SimHash."""
        self._entries[entry_id] = simhash

    def is_duplicate(
        self, entry_id: str, text: str, *, exclude_self: bool = True,
    ) -> bool:
        """Check if text is a near-duplicate of any existing entry."""
        new_hash = compute_simhash(text)
        for eid, existing in self._entries.items():
            if exclude_self and eid == entry_id:
                continue
            if hamming_distance(new_hash, existing) <= self.threshold:
                return True
        return False

    def find_duplicates(
        self, entry_id: str, text: str, *, exclude_self: bool = True,
    ) -> list[str]:
        """Return IDs of all near-duplicate entries."""
        new_hash = compute_simhash(text)
        dupes: list[str] = []
        for eid, existing in self._entries.items():
            if exclude_self and eid == entry_id:
                continue
            if hamming_distance(new_hash, existing) <= self.threshold:
                dupes.append(eid)
        return dupes

    def remove(self, entry_id: str) -> None:
        """Remove an entry from the index."""
        self._entries.pop(entry_id, None)

    def clear(self) -> None:
        """Clear all entries."""
        self._entries.clear()

    def size(self) -> int:
        return len(self._entries)

    def to_dict(self) -> dict[str, Any]:
        return {"threshold": self.threshold, "entries": dict(self._entries)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SimHashIndex:
        idx = cls(threshold=data.get("threshold", 3))
        idx._entries = dict(data.get("entries", {}))
        return idx


if __name__ == "__main__":
    idx = SimHashIndex()
    idx.add("1", "The quick brown fox jumps over the lazy dog")
    print(f"Duplicate: {idx.is_duplicate('2', 'The quick brown fox jumps over the lazy dog')}")
    print(f"Unique: {idx.is_duplicate('3', 'A completely different sentence about cats')}")
