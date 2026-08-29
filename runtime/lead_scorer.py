"""Lead scoring: combine fit, intent, and behavior into a 0-100 score.

Pure weighted scoring used by lead-generation / CRM workflows (2.7.10).
Each input is expected in [0, 1]; weights are configurable via constructor
injection. Raises ``ValidationError`` on out-of-range inputs.
"""

from __future__ import annotations

from runtime.schemas import ValidationError

DEFAULT_WEIGHTS: dict[str, float] = {
    "fit": 0.4,
    "intent": 0.35,
    "behavior": 0.25,
}


class LeadScorer:
    """Scores leads from three normalized signals."""

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        self._weights = dict(weights or DEFAULT_WEIGHTS)
        total = sum(self._weights.values())
        if total <= 0:
            raise ValidationError(
                "weights must sum to a positive value",
                context={"weights": self._weights},
            )
        self._weights = {k: v / total for k, v in self._weights.items()}

    def score_lead(self, fit: float, intent: float, behavior: float) -> int:
        """Return a 0-100 lead score.

        Args:
            fit: How well the lead matches the ideal customer (0-1).
            intent: Demonstrated purchase intent (0-1).
            behavior: Engagement / behavioral signals (0-1).

        Raises:
            ValidationError: if any input is outside [0, 1].
        """
        for name, value in (("fit", fit), ("intent", intent), ("behavior", behavior)):
            if not 0.0 <= value <= 1.0:
                raise ValidationError(
                    f"{name} must be in [0, 1]",
                    context={name: value},
                )
        raw = (
            fit * self._weights["fit"]
            + intent * self._weights["intent"]
            + behavior * self._weights["behavior"]
        )
        return round(raw * 100)


def score_lead(fit: float, intent: float, behavior: float) -> int:
    """Module-level convenience wrapper using default weights."""
    return LeadScorer().score_lead(fit, intent, behavior)
