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


@dataclass
class TemporalFact:
    """A fact with temporal validity window."""

    subject: str
    predicate: str
    object: str
    valid_from: str  # ISO date string
    valid_to: str | None = None  # None = still valid

    def is_valid_at(self, at: str) -> bool:
        """Check if this fact was valid at the given time."""
        if at < self.valid_from:
            return False
        return not (self.valid_to and at >= self.valid_to)


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
        """Set a new fact, closing any currently-valid fact with same s+p."""
        now = datetime.now(timezone.utc).isoformat()
        vf = valid_from or now
        # Close any currently-valid fact with same subject+predicate
        for fact in self._facts:
            if (fact.subject == subject and fact.predicate == predicate
                    and fact.valid_to is None and vf >= fact.valid_from):
                fact.valid_to = vf
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
        for fact in reversed(self._facts):  # Most recent first
            if (fact.subject == subject and fact.predicate == predicate
                    and fact.is_valid_at(query_time)):
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
        """Get the full history of a fact (all versions)."""
        return [
            f for f in self._facts
            if f.subject == subject and f.predicate == predicate
        ]

    def count(self) -> int:
        return len(self._facts)


if __name__ == "__main__":
    store = TemporalFactStore()
    store.set_fact("project", "status", "development", "2024-01-01")
    store.set_fact("project", "status", "production", "2024-06-01")
    print(f"At 2024-03-01: {store.query_fact('project', 'status', at='2024-03-01')}")
    print(f"At 2024-07-01: {store.query_fact('project', 'status', at='2024-07-01')}")
