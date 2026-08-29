"""Freelance pipeline analytics: bids, win/loss, and proposal A/B.

Tracks bidding outcomes by platform/niche and proposal variants to surface
win rates and the best-performing proposal. Inspired by the win/loss
analytics gap in the freelance report (2.7.9). Pure-Python aggregation.
"""

from __future__ import annotations

from dataclasses import dataclass

from runtime.schemas import ValidationError


@dataclass
class _Bid:
    platform: str
    niche: str
    amount: float
    won: bool | None


@dataclass
class _ProposalVariant:
    variant: str
    wins: int = 0
    losses: int = 0


class PipelineAnalytics:
    """Aggregates bidding and proposal outcomes."""

    def __init__(self) -> None:
        self._bids: list[_Bid] = []
        self._variants: dict[str, _ProposalVariant] = {}

    def record_bid(
        self, platform: str, niche: str, amount: float, won: bool | None
    ) -> None:
        """Record a bid outcome.

        Args:
            platform: Platform the bid was placed on (e.g. "upwork").
            niche: Niche / skill category.
            amount: Bid amount.
            won: True if won, False if lost, None if still pending.
        """
        if won is not None and not isinstance(won, bool):
            raise ValidationError("won must be bool or None")
        if amount < 0:
            raise ValidationError("amount must be non-negative")
        self._bids.append(_Bid(platform=platform, niche=niche, amount=amount, won=won))

    def record_proposal_variant(self, variant: str, won: bool) -> None:
        """Record a proposal-variant outcome (won True/False)."""
        entry = self._variants.setdefault(variant, _ProposalVariant(variant=variant))
        if won:
            entry.wins += 1
        else:
            entry.losses += 1

    def win_rate(self, platform: str | None = None, niche: str | None = None) -> float:
        """Return overall (or filtered) win rate in [0, 1]."""
        decided = [b for b in self._bids if b.won is not None]
        if platform is not None:
            decided = [b for b in decided if b.platform == platform]
        if niche is not None:
            decided = [b for b in decided if b.niche == niche]
        if not decided:
            return 0.0
        wins = sum(1 for b in decided if b.won)
        return wins / len(decided)

    def proposal_ab_winner(self) -> str | None:
        """Return the proposal variant with the highest win rate, or None."""
        best: str | None = None
        best_rate = -1.0
        for variant in self._variants.values():
            total = variant.wins + variant.losses
            if total == 0:
                continue
            rate = variant.wins / total
            if rate > best_rate:
                best_rate = rate
                best = variant.variant
        return best
