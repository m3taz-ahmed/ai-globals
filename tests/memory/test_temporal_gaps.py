"""Gap tests for memory/temporal.py — parse fallbacks and edge cases."""

from __future__ import annotations

from memory.temporal import TemporalFact, TemporalFactStore, _parse_time


class TestParseTime:
    def test_iso(self):
        dt = _parse_time("2024-03-15T10:00:00")
        assert dt.year == 2024 and dt.tzinfo is not None

    def test_date_only(self):
        assert _parse_time("2024-03-15").hour == 0

    def test_unpadded_date_fallback(self):
        # "2024-1-5" fails fromisoformat (needs zero-padding) → strptime path
        dt = _parse_time("2024-1-5")
        assert dt.month == 1 and dt.day == 5


class TestIsValidAt:
    def test_bad_at(self):
        f = TemporalFact("s", "p", "o", valid_from="2024-01-01")
        assert f.is_valid_at("not-a-time") is False

    def test_bad_valid_from(self):
        f = TemporalFact("s", "p", "o", valid_from="!!!")
        assert f.is_valid_at("2024-01-01") is False

    def test_before_start(self):
        f = TemporalFact("s", "p", "o", valid_from="2024-01-01")
        assert f.is_valid_at("2023-01-01") is False

    def test_after_close(self):
        f = TemporalFact("s", "p", "o", valid_from="2024-01-01",
                         valid_to="2024-06-01")
        assert f.is_valid_at("2024-03-01") is True
        assert f.is_valid_at("2024-07-01") is False

    def test_bad_valid_to(self):
        f = TemporalFact("s", "p", "o", valid_from="2024-01-01",
                         valid_to="!!!")
        assert f.is_valid_at("2024-03-01") is False


class TestStore:
    def test_dedup_identical(self):
        s = TemporalFactStore()
        a = s.set_fact("X", "has_ceo", "Alice", "2020-01-01")
        b = s.set_fact("X", "has_ceo", "Alice", "2020-01-01")
        assert a is b and s.count() == 1

    def test_close_on_update(self):
        s = TemporalFactStore()
        s.set_fact("X", "has_ceo", "Alice", "2020-01-01")
        s.set_fact("X", "has_ceo", "Bob", "2024-01-01")
        assert s.query_fact("X", "has_ceo", at="2021-01-01") == "Alice"
        assert s.query_fact("X", "has_ceo", at="2024-06-01") == "Bob"

    def test_backfill_keeps_nonoverlap(self):
        s = TemporalFactStore()
        s.set_fact("X", "p", "new", "2024-01-01")
        # backfill earlier than open fact → open fact closes at its own start
        s.set_fact("X", "p", "old", "2020-01-01")
        hist = s.history("X", "p")
        assert hist[0].object == "old"

    def test_invalid_valid_from_falls_back(self):
        s = TemporalFactStore()
        f = s.set_fact("X", "p", "o", valid_from="not-a-date")
        assert "T" in f.valid_from  # fell back to now (ISO with time)

    def test_open_fact_bad_start(self):
        s = TemporalFactStore()
        # craft an open fact with unparseable valid_from directly
        s._facts.append(TemporalFact("X", "p", "weird", valid_from="@@@"))
        s.set_fact("X", "p", "new", "2024-01-01")
        # open_start parse failed → close_at = vf path exercised
        assert s._facts[0].valid_to is not None

    def test_query_none(self):
        s = TemporalFactStore()
        assert s.query_fact("nobody", "p") is None

    def test_query_all_facts_filters(self):
        s = TemporalFactStore()
        s.set_fact("A", "p", "1", "2020-01-01")
        s.set_fact("B", "p", "2", "2020-01-01")
        assert len(s.query_all_facts()) == 2
        assert len(s.query_all_facts(subject="A")) == 1
        assert len(s.query_all_facts(at="1999-01-01")) == 0

    def test_history_sorted_with_bad_date(self):
        s = TemporalFactStore()
        s._facts.append(TemporalFact("X", "p", "bad", valid_from="@@@"))
        s.set_fact("X", "p", "good", "2020-01-01")
        hist = s.history("X", "p")
        # bad-date fact falls back to raw-string sort key ("@@@" > "2020-…")
        assert hist[0].object == "good" and hist[-1].object == "bad"

    def test_count(self):
        s = TemporalFactStore()
        assert s.count() == 0
        s.set_fact("A", "p", "1")
        assert s.count() == 1
