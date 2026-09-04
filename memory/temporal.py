#!/usr/bin/env python3
"""Temporal Knowledge Graph — point-in-time truth tracking (from OpenMemory).

Stores facts with validity windows (valid_from / valid_to). When a
fact changes, the previous version's valid_to is closed and a new
version is created. This enables point-in-time queries.

Usage::

    from memory.temporal import TemporalFactStore

    store = TemporalFactStore()
    store.set_fact("CompanyX", "has_CEO", "Alice", valid_from="2021-01-01")
    store.set_fact("CompanyX", "has_CEO", "Bob", valid_from="2024-04-10")
    # Query at specific time
    ceo = store.query_fact("CompanyX", "has_CEO", at="2022-06-01")
    assert ceo == "Alice"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


def _parse_time(value: str) -> datetime:
    """Parse an ISO timestamp; date-only strings become start-of-day UTC."""
    text = value.strip()
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        dt = datetime.strptime(text, "%Y-%m-%d")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


@dataclass
class TemporalFact:
    """A fact with temporal validity window."""

    subject: str
    predicate: str
    object: str
    valid_from: str  # ISO date string
    valid_to: str | None = None  # None = still valid

    def is_valid_at(self, at: str) -> bool:
        """Check if this fact was valid at the given time (parsed, not string-compared)."""
        try:
            moment = _parse_time(at)
            start = _parse_time(self.valid_from)
        except ValueError:
            return False
        if moment < start:
            return False
        if self.valid_to:
            try:
                return moment < _parse_time(self.valid_to)
            except ValueError:
                return False
        return True


@dataclass
class TemporalFactStore:
    """Temporal knowledge graph with validity windows (from OpenMemory).

    Facts are stored as (subject, predicate, object) triples with
    temporal validity. When a new fact is set, any currently-valid
    fact with the same subject+predicate gets its valid_to closed.
    """

    _facts: list[TemporalFact] = field(default_factory=list)

    def set_fact(
        self,
        subject: str,
        predicate: str,
        object: str,
        valid_from: str | None = None,
    ) -> TemporalFact:
        """Set a new fact, closing any currently-valid fact with same s+p.

        Backfills (vf earlier than the current open fact) close the open
        fact at the new fact's start and keep windows non-overlapping;
        identical re-sets are deduplicated (returned as-is).
        """
        now = datetime.now(timezone.utc).isoformat()
        vf = valid_from or now
        try:
            vf_dt = _parse_time(vf)
        except ValueError:
            vf = now
            vf_dt = _parse_time(now)
        for fact in self._facts:
            if fact.subject != subject or fact.predicate != predicate:
                continue
            if fact.object == object and fact.valid_to is None:
                return fact  # identical open fact: dedup, no new version
            if fact.valid_to is None:
                try:
                    open_start = _parse_time(fact.valid_from)
                except ValueError:
                    open_start = vf_dt
                # Close the open version at the later of the two starts so
                # windows never overlap.
                close_at = vf if vf_dt >= open_start else fact.valid_from
                fact.valid_to = close_at
        new_fact = TemporalFact(
            subject=subject, predicate=predicate, object=object,
            valid_from=vf,
        )
        self._facts.append(new_fact)
        return new_fact

    def query_fact(
        self,
        subject: str,
        predicate: str,
        at: str | None = None,
    ) -> str | None:
        """Query the value of a fact at a specific point in time."""
        now = datetime.now(timezone.utc).isoformat()
        query_time = at or now
        for fact in reversed(self.history(subject, predicate)):
            if fact.is_valid_at(query_time):
                return fact.object
        return None

    def query_all_facts(
        self,
        subject: str | None = None,
        at: str | None = None,
    ) -> list[TemporalFact]:
        """Query all facts, optionally filtered by subject and time."""
        now = datetime.now(timezone.utc).isoformat()
        query_time = at or now
        results = []
        for fact in self._facts:
            if subject and fact.subject != subject:
                continue
            if fact.is_valid_at(query_time):
                results.append(fact)
        return results

    def history(
        self,
        subject: str,
        predicate: str,
    ) -> list[TemporalFact]:
        """Get the full history of a fact (all versions, chronological)."""
        matched = [
            f for f in self._facts
            if f.subject == subject and f.predicate == predicate
        ]
        def _sort_key(f: TemporalFact) -> str:
            try:
                return _parse_time(f.valid_from).isoformat()
            except ValueError:
                return f.valid_from
        return sorted(matched, key=_sort_key)

    def count(self) -> int:
        return len(self._facts)


if __name__ == "__main__":
    store = TemporalFactStore()
    store.set_fact("project", "status", "development", "2024-01-01")
    store.set_fact("project", "status", "production", "2024-06-01")
    print(f"At 2024-03-01: {store.query_fact('project', 'status', at='2024-03-01')}")
    print(f"At 2024-07-01: {store.query_fact('project', 'status', at='2024-07-01')}")
