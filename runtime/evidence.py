"""Evidence provenance tiers and ledger.

Adapted from the REA (morluto/rea, MIT) evidence model: every reported fact
carries a tier distinguishing how it was established. Unresolved identity or
applicability stays ``UNKNOWN`` - never treated as absent, foreign, or
aligned. Consumers derive completeness from examined coverage, not from the
absence of records.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EvidenceTier(str, Enum):
    """How a reported fact was established (ordered by epistemic strength)."""

    OBSERVATION = "observation"  # directly measured: pattern match, tool output, file contents
    DERIVATION = "derivation"    # computed from observations: counts, adjusted severity, advisory matches
    INFERENCE = "inference"      # reasoned judgment; may be wrong - state the reasoning
    UNKNOWN = "unknown"          # unresolved; must surface as unknown, not be silently dropped


@dataclass(frozen=True)
class Evidence:
    """One reported fact with provenance and known limits.

    Attributes:
        tier: How the claim was established (see ``EvidenceTier``).
        claim: The fact being reported.
        source: Producer of the evidence (rule id, scanner, tool name).
        location: Where the evidence lives (``file:line``, offset, path, URL).
        limitations: Known bounds on what this evidence establishes.
    """

    tier: EvidenceTier
    claim: str
    source: str = ""
    location: str = ""
    limitations: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "tier": self.tier.value,
            "claim": self.claim,
            "source": self.source,
            "location": self.location,
            "limitations": self.limitations,
        }


@dataclass
class EvidenceLedger:
    """Ordered store of ``Evidence`` records with per-tier lookup.

    Unknowns are retained (never filtered out on write) so a report's
    blind spots are inspectable alongside its findings.
    """

    records: list[Evidence] = field(default_factory=list)

    def record(
        self,
        tier: EvidenceTier,
        claim: str,
        source: str = "",
        location: str = "",
        limitations: str = "",
    ) -> Evidence:
        """Append and return a new evidence record."""
        ev = Evidence(tier, claim, source=source, location=location, limitations=limitations)
        self.records.append(ev)
        return ev

    def by_tier(self, tier: EvidenceTier) -> list[Evidence]:
        """All records at the given tier, in insertion order."""
        return [r for r in self.records if r.tier is tier]

    @property
    def unknowns(self) -> list[Evidence]:
        """Records whose resolution is still open."""
        return self.by_tier(EvidenceTier.UNKNOWN)

    def summary(self) -> dict[str, int]:
        """Per-tier record counts (all tiers present, zero-filled)."""
        counts = {t.value: 0 for t in EvidenceTier}
        for r in self.records:
            counts[r.tier.value] += 1
        return counts

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary(),
            "records": [r.to_dict() for r in self.records],
        }
