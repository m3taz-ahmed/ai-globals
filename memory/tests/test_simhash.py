"""Tests for memory/simhash.py — near-duplicate detection."""

from __future__ import annotations

from memory.simhash import SimHashIndex, compute_simhash, hamming_distance


class TestSimHash:
    def test_identical_text_same_hash(self) -> None:
        h1 = compute_simhash("The quick brown fox")
        h2 = compute_simhash("The quick brown fox")
        assert h1 == h2

    def test_different_text_different_hash(self) -> None:
        h1 = compute_simhash("The quick brown fox")
        h2 = compute_simhash("A completely different sentence about cats")
        assert h1 != h2

    def test_empty_text_returns_zero(self) -> None:
        assert compute_simhash("") == "0" * 16

    def test_hamming_distance_zero_for_identical(self) -> None:
        h = compute_simhash("test text")
        assert hamming_distance(h, h) == 0

    def test_hamming_distance_positive_for_different(self) -> None:
        h1 = compute_simhash("apple banana cherry")
        h2 = compute_simhash("dog elephant fish")
        assert hamming_distance(h1, h2) > 0


class TestSimHashIndex:
    def test_add_and_is_duplicate_true(self) -> None:
        idx = SimHashIndex()
        idx.add("1", "The quick brown fox jumps over the lazy dog")
        assert idx.is_duplicate("2", "The quick brown fox jumps over the lazy dog") is True

    def test_is_duplicate_false_for_unique(self) -> None:
        idx = SimHashIndex()
        idx.add("1", "The quick brown fox jumps over the lazy dog")
        assert idx.is_duplicate("2", "A completely different sentence about quantum physics") is False

    def test_find_duplicates_returns_ids(self) -> None:
        idx = SimHashIndex(threshold=10)
        idx.add("1", "The quick brown fox jumps over the lazy dog today")
        idx.add("2", "The quick brown fox jumps over the lazy dog now")
        dupes = idx.find_duplicates("3", "The quick brown fox jumps over the lazy dog")
        assert "1" in dupes
        assert "2" in dupes

    def test_exclude_self(self) -> None:
        idx = SimHashIndex()
        idx.add("1", "The quick brown fox")
        dupes = idx.find_duplicates("1", "The quick brown fox", exclude_self=True)
        assert "1" not in dupes
        dupes_self = idx.find_duplicates("1", "The quick brown fox", exclude_self=False)
        assert "1" in dupes_self

    def test_remove_entry(self) -> None:
        idx = SimHashIndex()
        idx.add("1", "test text")
        idx.remove("1")
        assert idx.size() == 0

    def test_clear(self) -> None:
        idx = SimHashIndex()
        idx.add("1", "a")
        idx.add("2", "b")
        idx.clear()
        assert idx.size() == 0

    def test_to_dict_and_from_dict(self) -> None:
        idx = SimHashIndex(threshold=5)
        idx.add("1", "test text")
        d = idx.to_dict()
        restored = SimHashIndex.from_dict(d)
        assert restored.threshold == 5
        assert restored.size() == 1

    def test_threshold_controls_sensitivity(self) -> None:
        idx_strict = SimHashIndex(threshold=0)
        idx_loose = SimHashIndex(threshold=20)
        idx_strict.add("1", "apple banana cherry fruit")
        idx_loose.add("1", "apple banana cherry fruit")
        # Similar text — loose threshold catches it, strict doesn't
        similar = "apple banana cherry apple"
        assert idx_loose.is_duplicate("2", similar) is True
        assert idx_strict.is_duplicate("2", similar) is False
