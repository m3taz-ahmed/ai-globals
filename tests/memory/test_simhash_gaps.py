"""Gap tests for memory/simhash.py."""
from __future__ import annotations

import pytest

from memory.simhash import (
    SimHashIndex,
    compute_simhash,
    hamming_distance,
)


class TestHamming:
    def test_invalid_hash_raises(self):
        with pytest.raises(ValueError, match="Invalid SimHash"):
            hamming_distance("xyz", "0" * 16)

    def test_valid_distance(self):
        assert hamming_distance("0" * 16, "f" * 16) == 64


class TestIndex:
    def test_add_hash_and_size(self):
        idx = SimHashIndex()
        idx.add_hash("a", "0" * 16)
        assert idx.size() == 1

    def test_is_duplicate_empty_hash(self):
        idx = SimHashIndex()
        assert idx.is_duplicate("x", "!!!") is False  # tokenless -> ""

    def test_exclude_self(self):
        idx = SimHashIndex()
        h = idx.add("a", "the quick brown fox")
        assert idx.is_duplicate("a", "the quick brown fox") is False  # excluded
        assert idx.is_duplicate("a", "the quick brown fox", exclude_self=False) is True
        _ = h

    def test_invalid_existing_skipped(self):
        idx = SimHashIndex()
        idx.add_hash("bad", "notahash")
        assert idx.is_duplicate("x", "the quick brown fox") is False

    def test_find_duplicates_empty_and_self(self):
        idx = SimHashIndex()
        assert idx.find_duplicates("x", "!!!") == []
        idx.add("a", "the quick brown fox")
        assert idx.find_duplicates("a", "the quick brown fox") == []

    def test_find_duplicates_invalid_existing(self):
        idx = SimHashIndex()
        idx.add_hash("bad", "zz")
        idx.add_hash("good", "0" * 16)
        idx.add_hash("me", compute_simhash("the quick brown fox"))
        found = idx.find_duplicates("me", "the quick brown fox")
        assert "bad" not in found


class TestFromDict:
    def test_non_mapping(self):
        with pytest.raises(ValueError, match="must be a mapping"):
            SimHashIndex.from_dict([1, 2])

    def test_bad_threshold_defaults(self):
        idx = SimHashIndex.from_dict({"threshold": "nope", "entries": {}})
        assert idx.threshold == 3

    def test_non_dict_entries(self):
        with pytest.raises(ValueError, match="'entries' must be a mapping"):
            SimHashIndex.from_dict({"entries": [1]})

    def test_entries_filtered(self):
        idx = SimHashIndex.from_dict(
            {"threshold": 5, "entries": {"a": "0" * 16, "b": "bad"}}
        )
        assert idx.threshold == 5
        assert idx.size() == 1
