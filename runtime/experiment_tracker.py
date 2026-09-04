"""A/B experiment statistics engine.

Implements a two-proportion z-test with p-value, a Sample Ratio Mismatch
(SRM) check, and a winner decision. Inspired by GrowthBook's stats module
(2.7.2). CUPED variance reduction and full Bayesian estimation are noted
as extensions and can be requested via ``method``.

No network calls. Raises ``ValidationError`` on invalid counts and
``NotImplementedError`` only when an advanced method is explicitly requested.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from runtime.schemas import ValidationError


def _normal_cdf(x: float) -> float:
    """Standard normal CDF via the error function."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _two_proportion_z(
    a_conv: int, a_vis: int, b_conv: int, b_vis: int
) -> tuple[float, float, float, float]:
    """Return (p_a, p_b, z, two_tailed_p)."""
    p_a = a_conv / a_vis
    p_b = b_conv / b_vis
    pooled = (a_conv + b_conv) / (a_vis + b_vis)
    pooled_se = math.sqrt(pooled * (1.0 - pooled) * (1.0 / a_vis + 1.0 / b_vis))
    if pooled_se == 0 or a_conv == 0 or b_conv == 0:
        # Pooled SE collapses to 0 when either arm has 0 conversions;
        # fall back to unpooled SE so the z-score stays meaningful.
        unpooled = math.sqrt(p_a * (1.0 - p_a) / a_vis + p_b * (1.0 - p_b) / b_vis)
        se = unpooled
    else:
        se = pooled_se
    z = 0.0 if se == 0 else (p_a - p_b) / se
    p_value = 2.0 * (1.0 - _normal_cdf(abs(z)))
    return p_a, p_b, z, p_value


def _srm_p_value(a_vis: int, b_vis: int, expected_ratio: float = 0.5) -> float:
    """Chi-square SRM test against an expected split.

    Returns the p-value for the hypothesis that the observed visitor split
    matches ``expected_ratio`` (default 50/50). Low p (<0.01) signals a
    broken assignment / tracking.
    """
    total = a_vis + b_vis
    if total == 0:
        return 1.0
    exp_a = total * expected_ratio
    exp_b = total * (1.0 - expected_ratio)
    if exp_a == 0 or exp_b == 0:
        return 1.0
    chi = (a_vis - exp_a) ** 2 / exp_a + (b_vis - exp_b) ** 2 / exp_b
    # chi-square with 1 dof: CDF = erf(sqrt(chi/2))
    return 1.0 - math.erf(math.sqrt(chi / 2.0))


@dataclass
class ABResult:
    """Structured result of an A/B analysis."""

    p_a: float
    p_b: float
    z: float
    p_value: float
    srm_p_value: float
    srm_ok: bool
    significant: bool
    winner: str | None
    method: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "p_a": self.p_a,
            "p_b": self.p_b,
            "z": self.z,
            "p_value": self.p_value,
            "srm_p_value": self.srm_p_value,
            "srm_ok": self.srm_ok,
            "significant": self.significant,
            "winner": self.winner,
            "method": self.method,
        }

    # Backward-compat: allow dict-style reads (result["p_a"]) for callers
    # pinned to the old raw-dict return shape.
    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.to_dict().get(key, default)


def analyze_ab_test(
    a_conv: int,
    a_vis: int,
    b_conv: int,
    b_vis: int,
    confidence: float = 0.95,
    method: str = "z_test",
    expected_ratio: float = 0.5,
) -> ABResult:
    """Analyze a two-variant A/B test.

    Args:
        a_conv: Conversions in variant A.
        a_vis: Visitors in variant A.
        b_conv: Conversions in variant B.
        b_vis: Visitors in variant B.
        confidence: Confidence level (e.g. 0.95).
        method: ``"z_test"`` (default) or an advanced method. Requesting
            ``"cuped"`` or ``"bayesian"`` raises ``NotImplementedError``.
        expected_ratio: Expected share for variant A in the SRM check
            (default 0.5 for 50/50).

    Returns:
        ABResult with conversion rates, z, p-value, SRM diagnostics, and the
        winning variant (``"A"``/``"B"``/``None``). Use ``.to_dict()`` for
        the legacy dict shape.

    Raises:
        ValidationError: on non-positive visitor counts, bad confidence,
            negative conversions, conversions exceeding visitors, or when
            an advanced ``method`` is requested.
    """
    if method not in ("z_test",):
        raise ValidationError(
            f"method '{method}' is planned (CUPED/Bayesian extension); "
            "not implemented yet",
            context={"method": method},
        )
    if a_vis <= 0 or b_vis <= 0:
        raise ValidationError(
            "visitor counts must be positive",
            context={"a_vis": a_vis, "b_vis": b_vis},
        )
    if not 0.0 < confidence < 1.0:
        raise ValidationError(
            "confidence must be in (0, 1)", context={"confidence": confidence}
        )
    if any(v < 0 for v in (a_conv, b_conv)):
        raise ValidationError("conversions cannot be negative")
    if a_conv > a_vis or b_conv > b_vis:
        raise ValidationError(
            "conversions cannot exceed visitors",
            context={"a_conv": a_conv, "a_vis": a_vis, "b_conv": b_conv, "b_vis": b_vis},
        )

    p_a, p_b, z, p_value = _two_proportion_z(a_conv, a_vis, b_conv, b_vis)
    srm = _srm_p_value(a_vis, b_vis, expected_ratio)
    srm_ok = srm >= 0.01
    alpha = 1.0 - confidence
    significant = p_value < alpha

    if not significant:
        winner: str | None = None
    elif p_a > p_b:
        winner = "A"
    else:
        winner = "B"

    return ABResult(
        p_a=p_a,
        p_b=p_b,
        z=z,
        p_value=p_value,
        srm_p_value=srm,
        srm_ok=srm_ok,
        significant=significant,
        winner=winner,
        method=method,
    )


def analyze_ab_test_dict(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Backward-compat dict alias for :func:`analyze_ab_test`."""
    return analyze_ab_test(*args, **kwargs).to_dict()
