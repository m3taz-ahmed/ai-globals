#!/usr/bin/env python3
"""Advanced budget features: progressive throttling, reserve/settle,
burn forecasting, spend anomaly detection, model cost optimization,
and shadow mode tracking.

Extends ``runtime/budget.py`` and ``runtime/budget_escalation.py`` with
finer-grained controls:

* **Progressive throttling** — model downgrades at configurable
  utilization tiers (advisory / throttle / restrict / hard-stop).
* **Reserve & settle** — atomic cost holds that are reserved before a
  call and settled to the actual amount afterwards (like a credit-card
  pre-auth).
* **Burn forecasting** — rolling-window spend velocity with ETA and
  breach prediction.
* **Spend anomaly detection** — z-score based outlier detection on
  individual spend events.
* **Model cost optimizer** — pricing table for 30+ models with
  comparison, recommendation, and savings projection.
* **Shadow mode** — record what *would* have tripped throttling without
  actually enforcing it, for safe rollout of new thresholds.

Usage::

    from runtime.budget_advanced import (
        ReserveSettleProtocol, BurnForecaster, ModelCostOptimizer,
    )
    rsp = ReserveSettleProtocol()
    hold = rsp.reserve("session-abc", 0.50)
    # ... call completes ...
    rsp.settle(hold.hold_id, 0.42)
"""

from __future__ import annotations

import logging
import math
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum
from typing import Any, ClassVar

from runtime.schemas import AizeeError, ErrorSeverity

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Progressive throttling
# ---------------------------------------------------------------------------


class ThrottleTier(str, Enum):
    """Progressive throttling tiers as budget utilization increases.

    Each tier maps to a utilization percentage threshold. The budget
    manager selects the *highest* tier whose threshold has been crossed.
    """

    ADVISORY = "advisory"    # 60% — log, suggest cheaper model
    THROTTLE = "throttle"    # 75% — force model downgrade
    RESTRICT = "restrict"    # 90% — block expensive ops
    HARD_STOP = "hard_stop"  # 100% — block all spending


@dataclass
class ThrottleConfig:
    """Configuration for progressive budget throttling.

    Thresholds are utilization fractions (0.0-1.0) and must be sorted
    ascending (advisory < throttle < restrict < hard_stop).

    ``throttle_model`` / ``restrict_model`` are the model names to
    downgrade *to* at the respective tiers (``None`` = no forced model).
    """

    advisory_pct: float = 0.60
    throttle_pct: float = 0.75
    restrict_pct: float = 0.90
    hard_stop_pct: float = 1.0
    throttle_model: str | None = None
    restrict_model: str | None = None

    def __post_init__(self) -> None:
        bands = [
            self.advisory_pct,
            self.throttle_pct,
            self.restrict_pct,
            self.hard_stop_pct,
        ]
        if bands != sorted(bands):
            raise ValueError(
                f"ThrottleConfig thresholds must be sorted ascending, got {bands!r}"
            )
        for b in bands:
            if not 0.0 <= b <= 1.0:
                raise ValueError(f"ThrottleConfig threshold {b} out of range [0,1]")


def compute_throttle_tier(
    spend: float,
    limit: float,
    config: ThrottleConfig | None = None,
) -> ThrottleTier | None:
    """Return the highest throttle tier whose threshold has been crossed.

    Returns ``None`` if utilization is below the advisory tier.
    """
    if config is None:
        config = ThrottleConfig()
    if limit <= 0:
        return None
    util = spend / limit
    if util >= config.hard_stop_pct:
        return ThrottleTier.HARD_STOP
    if util >= config.restrict_pct:
        return ThrottleTier.RESTRICT
    if util >= config.throttle_pct:
        return ThrottleTier.THROTTLE
    if util >= config.advisory_pct:
        return ThrottleTier.ADVISORY
    return None


# ---------------------------------------------------------------------------
# Burn forecasting
# ---------------------------------------------------------------------------


@dataclass
class BurnForecast:
    """Forecast of spend velocity and breach prediction for a scope.

    Attributes:
        scope: The budget scope identifier (e.g. session ID).
        period: The budget period label (e.g. "hourly", "daily").
        spend_velocity: Spend per minute based on the rolling window.
        eta_to_limit_seconds: Estimated seconds until the limit is
            reached (``None`` if velocity is zero or no limit).
        will_breach: Whether the projected end-of-period spend exceeds
            the limit.
        confidence: Forecast confidence in [0, 1] — higher with more
            samples in the window.
        projected_end_spend: Estimated total spend at period end.
    """

    scope: str
    period: str
    spend_velocity: float
    eta_to_limit_seconds: float | None
    will_breach: bool
    confidence: float
    projected_end_spend: float


class BurnForecaster:
    """Rolling-window spend velocity tracker with breach prediction.

    Records individual spend events per scope and computes:
    * **Velocity** — spend per minute over the rolling window.
    * **ETA** — estimated seconds until the budget limit is reached.
    * **Breach prediction** — whether projected end-of-period spend
      will exceed the limit.

    The window is a sliding time window (default 1 hour). Older events
    are evicted lazily on each ``record`` / ``forecast`` call.
    """

    def __init__(self, window_seconds: float = 3600.0) -> None:
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        self._window_seconds = window_seconds
        self._events: dict[str, deque[tuple[float, float]]] = defaultdict(deque)
        self._lock = threading.RLock()

    def record(self, scope: str, amount: float) -> None:
        """Record a spend event for *scope*."""
        if amount < 0:
            _logger.warning("Negative spend recorded for %s: %s", scope, amount)
        now = time.time()
        with self._lock:
            self._events[scope].append((now, amount))
            self._evict(scope, now)

    def forecast(
        self,
        scope: str,
        limit: float,
        period: str = "session",
    ) -> BurnForecast:
        """Compute a burn forecast for *scope* against *limit*."""
        now = time.time()
        with self._lock:
            self._evict(scope, now)
            events = list(self._events[scope])
        window_secs = max(self._window_seconds, 1.0)
        total = sum(amt for _ts, amt in events)
        velocity_per_min = (total / window_secs) * 60.0
        confidence = min(1.0, len(events) / 30.0)
        eta, will_breach, projected_end = self._project(
            limit, total, velocity_per_min, window_secs,
        )
        return BurnForecast(
            scope=scope, period=period,
            spend_velocity=velocity_per_min,
            eta_to_limit_seconds=eta, will_breach=will_breach,
            confidence=confidence, projected_end_spend=projected_end,
        )

    @staticmethod
    def _project(
        limit: float, total: float, velocity: float, window_secs: float,
    ) -> tuple[float | None, bool, float]:
        """Compute ETA, breach flag, and projected end spend."""
        eta: float | None = None
        will_breach = False
        projected_end = total
        if limit > 0 and velocity > 0:
            remaining = max(0.0, limit - total)
            eta = (remaining / velocity) * 60.0
            projected_end = velocity * (window_secs / 60.0)
            will_breach = projected_end >= limit
        return eta, will_breach, projected_end

    def _evict(self, scope: str, now: float) -> None:
        """Remove events older than the rolling window."""
        cutoff = now - self._window_seconds
        dq = self._events[scope]
        while dq and dq[0][0] < cutoff:
            dq.popleft()


# ---------------------------------------------------------------------------
# Spend anomaly detection
# ---------------------------------------------------------------------------


@dataclass
class SpendAnomaly:
    """Result of an anomaly check on a single spend event.

    Attributes:
        scope: The budget scope identifier.
        amount: The spend amount checked.
        z_score: Standardized score of the amount vs baseline.
        baseline_mean: Running mean of historical spend for the scope.
        baseline_std: Running standard deviation.
        is_anomaly: True if the z-score exceeds the threshold.
        timestamp: When the check was performed (epoch seconds).
    """

    scope: str
    amount: float
    z_score: float
    baseline_mean: float
    baseline_std: float
    is_anomaly: bool
    timestamp: float


class SpendAnomalyDetector:
    """Z-score based anomaly detector for individual spend events.

    Maintains a running mean and standard deviation per scope. When a
    new spend event is checked, its z-score is computed against the
    baseline. If the absolute z-score exceeds ``z_threshold`` (default
    2.0), it is flagged as an anomaly.

    A minimum number of samples (``min_samples``, default 10) must be
    accumulated before anomaly detection is active — earlier events
    are always reported as non-anomalous (insufficient baseline).
    """

    def __init__(
        self,
        min_samples: int = 10,
        z_threshold: float = 2.0,
    ) -> None:
        if min_samples < 2:
            raise ValueError("min_samples must be >= 2")
        if z_threshold <= 0:
            raise ValueError("z_threshold must be positive")
        self._min_samples = min_samples
        self._z_threshold = z_threshold
        self._samples: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.RLock()

    def record(self, scope: str, amount: float) -> None:
        """Record a spend event into the baseline for *scope*."""
        with self._lock:
            self._samples[scope].append(amount)

    def check(self, scope: str, amount: float) -> SpendAnomaly:
        """Check *amount* against the baseline for *scope*.

        The amount is also added to the baseline after the check, so
        repeated calls build up the running statistics.
        """
        now = time.time()
        with self._lock:
            samples = self._samples[scope]
            n = len(samples)
            if n < self._min_samples:
                self._samples[scope].append(amount)
                return self._no_anomaly(scope, amount, now)
            mean, std, z = self._compute_stats(samples, amount)
            is_anomaly = abs(z) >= self._z_threshold
            self._samples[scope].append(amount)
            return SpendAnomaly(
                scope=scope, amount=amount, z_score=round(z, 4),
                baseline_mean=round(mean, 6), baseline_std=round(std, 6),
                is_anomaly=is_anomaly, timestamp=now,
            )

    @staticmethod
    def _no_anomaly(scope: str, amount: float, now: float) -> SpendAnomaly:
        """Build a non-anomalous result (insufficient baseline)."""
        return SpendAnomaly(
            scope=scope, amount=amount, z_score=0.0,
            baseline_mean=0.0, baseline_std=0.0,
            is_anomaly=False, timestamp=now,
        )

    @staticmethod
    def _compute_stats(
        samples: list[float], amount: float,
    ) -> tuple[float, float, float]:
        """Compute mean, std, and z-score from samples."""
        n = len(samples)
        mean = sum(samples) / n
        variance = sum((x - mean) ** 2 for x in samples) / n
        std = math.sqrt(variance) if variance > 0 else 0.0
        z = (amount - mean) / std if std > 0 else 0.0
        return mean, std, z


# ---------------------------------------------------------------------------
# Reserve & settle protocol
# ---------------------------------------------------------------------------


@dataclass
class ReserveHold:
    """A cost hold reserved before a call, settled to actual cost after.

    Attributes:
        hold_id: Unique identifier for the hold.
        scope: The budget scope the hold is against.
        amount: The reserved amount.
        created_at: Creation timestamp (epoch seconds).
        expires_at: Expiry timestamp; expired holds are auto-released.
        settled: Whether the hold has been settled.
        settled_amount: The actual amount the hold was settled to.
    """

    hold_id: str
    scope: str
    amount: float
    created_at: float
    expires_at: float
    settled: bool = False
    settled_amount: float | None = None

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    @property
    def is_active(self) -> bool:
        return not self.settled and not self.is_expired

    def to_dict(self) -> dict[str, Any]:
        return {
            "hold_id": self.hold_id,
            "scope": self.scope,
            "amount": self.amount,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "settled": self.settled,
            "settled_amount": self.settled_amount,
        }


class ReserveSettleProtocol:
    """Atomic reserve-and-settle protocol for budget holds.

    Mirrors a credit-card pre-auth: before a call, ``reserve()`` places a
    hold for the estimated cost. After the call completes, ``settle()``
    adjusts the hold to the actual cost. ``release()`` cancels an
    unsettled hold (e.g. if the call failed).

    All operations are thread-safe via a re-entrant lock. Expired holds
    are lazily released on access.
    """

    def __init__(self) -> None:
        self._holds: dict[str, ReserveHold] = {}
        self._lock = threading.RLock()

    def reserve(
        self, scope: str, amount: float, ttl_seconds: float = 300.0,
    ) -> ReserveHold:
        """Atomically reserve *amount* for *scope*.

        Returns the created :class:`ReserveHold`. The hold will
        auto-expire after *ttl_seconds* if not settled or released.
        """
        if amount < 0:
            raise AizeeError(
                "INVALID_RESERVE",
                f"Cannot reserve negative amount {amount} for scope {scope!r}",
                ErrorSeverity.MEDIUM,
            )
        now = time.time()
        hold = ReserveHold(
            hold_id=uuid.uuid4().hex, scope=scope, amount=amount,
            created_at=now, expires_at=now + ttl_seconds,
        )
        with self._lock:
            self._purge_expired(scope)
            self._holds[hold.hold_id] = hold
        _logger.debug(
            "Reserved hold %s for scope %s amount %.4f ttl %.0fs",
            hold.hold_id[:8], scope, amount, ttl_seconds,
        )
        return hold

    def settle(self, hold_id: str, actual_amount: float) -> bool:
        """Settle a hold to the *actual* cost.

        Returns ``True`` if the hold was settled, ``False`` if the hold
        was not found, already settled, or expired.
        """
        with self._lock:
            hold = self._holds.get(hold_id)
            if hold is None or hold.settled or hold.is_expired:
                return False
            hold.settled = True
            hold.settled_amount = actual_amount
            _logger.debug(
                "Settled hold %s: reserved %.4f, actual %.4f",
                hold_id[:8], hold.amount, actual_amount,
            )
            return True

    def release(self, hold_id: str) -> bool:
        """Release (cancel) an unsettled hold.

        Returns ``True`` if the hold was released, ``False`` if not
        found or already settled.
        """
        with self._lock:
            hold = self._holds.get(hold_id)
            if hold is None or hold.settled:
                return False
            del self._holds[hold_id]
            _logger.debug("Released hold %s for scope %s", hold_id[:8], hold.scope)
            return True

    def get_hold(self, hold_id: str) -> ReserveHold | None:
        """Return the hold with *hold_id*, or ``None``."""
        with self._lock:
            return self._holds.get(hold_id)

    def available(self, scope: str, budget_limit: float) -> float:
        """Return available budget: limit - spent - reserved.

        *spent* is the sum of settled amounts; *reserved* is the sum of
        active (unsettled, unexpired) hold amounts.
        """
        with self._lock:
            self._purge_expired(scope)
            settled = 0.0
            reserved = 0.0
            for hold in self._holds.values():
                if hold.scope != scope:
                    continue
                if hold.settled and hold.settled_amount is not None:
                    settled += hold.settled_amount
                elif hold.is_active:
                    reserved += hold.amount
            return max(0.0, budget_limit - settled - reserved)

    def _purge_expired(self, scope: str) -> None:
        """Remove expired, unsettled holds for *scope*."""
        expired = [
            hid for hid, h in self._holds.items()
            if h.scope == scope and h.is_expired and not h.settled
        ]
        for hid in expired:
            del self._holds[hid]


# ---------------------------------------------------------------------------
# Model cost optimizer
# ---------------------------------------------------------------------------


class ModelCostOptimizer:
    """Pricing-aware model comparison and recommendation engine.

    Maintains a pricing table (per 1M tokens, input and output) for
    30+ models across OpenAI, Anthropic, Google, Meta, Mistral, and
    others. Provides:

    * ``compare()`` — cost comparison of the current model vs all
      alternatives.
    * ``recommend()`` — cheapest viable alternative at a given
      capability tier.
    * ``savings_projection()`` — projected monthly savings from
      switching models.

    Capability tiers group models by quality level so that
    ``recommend()`` doesn't suggest a downgrade that breaks task
    requirements.
    """

    # Per-1M-token pricing: (input_price, output_price) in USD.
    PRICING: ClassVar[dict[str, tuple[float, float]]] = {
        # OpenAI
        "gpt-4o": (2.50, 10.00),
        "gpt-4o-mini": (0.15, 0.60),
        "gpt-4-turbo": (10.00, 30.00),
        "gpt-4": (30.00, 60.00),
        "gpt-3.5-turbo": (0.50, 1.50),
        "o1": (15.00, 60.00),
        "o1-mini": (3.00, 12.00),
        "o1-preview": (15.00, 60.00),
        "o3-mini": (1.10, 4.40),
        # Anthropic
        "claude-3.5-sonnet": (3.00, 15.00),
        "claude-3.5-haiku": (0.80, 4.00),
        "claude-3-opus": (15.00, 75.00),
        "claude-3-sonnet": (3.00, 15.00),
        "claude-3-haiku": (0.25, 1.25),
        # Google
        "gemini-1.5-pro": (1.25, 5.00),
        "gemini-1.5-flash": (0.075, 0.30),
        "gemini-2.0-flash": (0.10, 0.40),
        "gemini-1.5-flash-8b": (0.0375, 0.15),
        # Meta (via Together/Groq/AWS; approximate)
        "llama-3.1-405b": (5.00, 15.00),
        "llama-3.1-70b": (0.90, 0.90),
        "llama-3.1-8b": (0.18, 0.18),
        "llama-3.3-70b": (0.59, 0.79),
        # Mistral
        "mistral-large": (2.00, 6.00),
        "mistral-medium": (0.40, 2.00),
        "mistral-small": (0.20, 0.60),
        "mistral-nemo": (0.15, 0.15),
        "codestral": (0.30, 0.90),
        # Cohere
        "command-r-plus": (2.50, 10.00),
        "command-r": (0.15, 0.60),
        # DeepSeek
        "deepseek-chat": (0.14, 0.28),
        "deepseek-reasoner": (0.55, 2.19),
        # xAI
        "grok-2": (2.00, 10.00),
    }

    # Capability tiers: model -> tier label.
    _CAPABILITY_TIERS: ClassVar[dict[str, str]] = {}

    @classmethod
    def _init_tiers(cls) -> None:
        if cls._CAPABILITY_TIERS:
            return
        high = {
            "gpt-4o", "gpt-4-turbo", "gpt-4", "o1", "o1-preview",
            "claude-3.5-sonnet", "claude-3-opus",
            "gemini-1.5-pro", "llama-3.1-405b", "mistral-large",
            "command-r-plus", "grok-2", "deepseek-reasoner",
        }
        medium = {
            "gpt-4o-mini", "o1-mini", "o3-mini", "gpt-3.5-turbo",
            "claude-3.5-haiku", "claude-3-sonnet",
            "gemini-2.0-flash", "llama-3.1-70b", "llama-3.3-70b",
            "mistral-medium", "command-r", "deepseek-chat",
        }
        for m in high:
            cls._CAPABILITY_TIERS[m] = "high"
        for m in medium:
            cls._CAPABILITY_TIERS[m] = "medium"
        for m in cls.PRICING:
            cls._CAPABILITY_TIERS.setdefault(m, "low")

    def __init__(self) -> None:
        self._init_tiers()

    def _cost_per_call(
        self,
        model: str,
        input_tokens: int = 1000,
        output_tokens: int = 500,
    ) -> float:
        """Compute cost for a single call to *model*."""
        pricing = self.PRICING.get(model)
        if pricing is None:
            raise AizeeError(
                "UNKNOWN_MODEL",
                f"Unknown model {model!r}; not in pricing table",
                ErrorSeverity.MEDIUM,
            )
        in_price, out_price = pricing
        return (input_tokens / 1_000_000) * in_price + (output_tokens / 1_000_000) * out_price

    def compare(
        self,
        current_model: str,
        input_tokens: int = 1000,
        output_tokens: int = 500,
    ) -> list[dict[str, Any]]:
        """Compare cost of *current_model* vs all alternatives.

        Returns a list of dicts sorted by cost ascending, each with:
        ``model``, ``cost_per_call``, ``savings_pct``, ``capability_tier``.
        """
        current_cost = self._cost_per_call(current_model, input_tokens, output_tokens)
        results: list[dict[str, Any]] = []
        for model in self.PRICING:
            cost = self._cost_per_call(model, input_tokens, output_tokens)
            savings = ((current_cost - cost) / current_cost * 100) if current_cost > 0 else 0.0
            results.append({
                "model": model,
                "cost_per_call": round(cost, 6),
                "savings_pct": round(savings, 2),
                "capability_tier": self._CAPABILITY_TIERS.get(model, "unknown"),
            })
        results.sort(key=lambda r: r["cost_per_call"])
        return results

    def recommend(
        self, current_model: str, capability_tier: str = "medium",
        input_tokens: int = 1000, output_tokens: int = 500,
    ) -> dict[str, Any]:
        """Recommend the cheapest viable alternative to *current_model*.

        *capability_tier* sets the minimum quality bar: ``"high"`` only
        considers high-tier models, ``"medium"`` considers medium and
        high, ``"low"`` considers all.
        """
        tier_order = {"low": 0, "medium": 1, "high": 2}
        min_level = tier_order.get(capability_tier, 1)
        current_cost = self._cost_per_call(current_model, input_tokens, output_tokens)
        candidates = self._find_cheaper(
            current_cost, min_level, tier_order, input_tokens, output_tokens,
        )
        if not candidates:
            return self._no_alternative(current_model, current_cost)
        candidates.sort(key=lambda r: r["cost_per_call"])
        return candidates[0]

    def _find_cheaper(
        self, current_cost: float, min_level: int,
        tier_order: dict[str, int], in_tok: int, out_tok: int,
    ) -> list[dict[str, Any]]:
        """Find all models cheaper than *current_cost* at or above tier."""
        candidates: list[dict[str, Any]] = []
        for model in self.PRICING:
            model_tier = self._CAPABILITY_TIERS.get(model, "low")
            if tier_order.get(model_tier, 0) < min_level:
                continue
            cost = self._cost_per_call(model, in_tok, out_tok)
            if cost < current_cost:
                savings = ((current_cost - cost) / current_cost * 100) if current_cost > 0 else 0.0
                candidates.append({
                    "model": model, "cost_per_call": round(cost, 6),
                    "savings_pct": round(savings, 2), "capability_tier": model_tier,
                })
        return candidates

    def _no_alternative(self, model: str, cost: float) -> dict[str, Any]:
        """Build a 'no cheaper alternative' result dict."""
        return {
            "model": model, "cost_per_call": round(cost, 6),
            "savings_pct": 0.0,
            "capability_tier": self._CAPABILITY_TIERS.get(model, "unknown"),
            "note": "No cheaper alternative at requested tier",
        }

    def savings_projection(
        self,
        current_model: str,
        recommended_model: str,
        monthly_calls: int,
        input_tokens: int = 1000,
        output_tokens: int = 500,
    ) -> dict[str, Any]:
        """Project monthly savings from switching models.

        Returns a dict with current/recommended monthly cost, absolute
        savings, and savings percentage.
        """
        current_per = self._cost_per_call(current_model, input_tokens, output_tokens)
        rec_per = self._cost_per_call(recommended_model, input_tokens, output_tokens)
        current_monthly = current_per * monthly_calls
        rec_monthly = rec_per * monthly_calls
        savings = current_monthly - rec_monthly
        pct = (savings / current_monthly * 100) if current_monthly > 0 else 0.0
        return {
            "current_model": current_model,
            "recommended_model": recommended_model,
            "monthly_calls": monthly_calls,
            "current_monthly_cost": round(current_monthly, 2),
            "recommended_monthly_cost": round(rec_monthly, 2),
            "monthly_savings": round(savings, 2),
            "savings_pct": round(pct, 2),
        }


# ---------------------------------------------------------------------------
# Shadow mode tracker
# ---------------------------------------------------------------------------


class ShadowModeTracker:
    """Records what *would* have tripped throttling without enforcing it.

    In shadow mode, the budget manager evaluates throttle tiers and
    records the outcome via ``record()`` but does not actually enforce
    the downgrade/block. This allows safe validation of new threshold
    configurations before enabling them in production.

    The tracker accumulates counts per scope and action type, plus the
    reasons for each would-be trip. ``report()`` returns a summary
    suitable for dashboards or governance review.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._entries: list[dict[str, Any]] = []
        self._counts: dict[str, dict[str, int]] = defaultdict(
            lambda: {"would_trip": 0, "total": 0}
        )

    def record(
        self,
        scope: str,
        action_type: str,
        would_trip: bool,
        reason: str,
    ) -> None:
        """Record a shadow-mode evaluation outcome."""
        entry = {
            "scope": scope,
            "action_type": action_type,
            "would_trip": would_trip,
            "reason": reason,
            "timestamp": time.time(),
        }
        with self._lock:
            self._entries.append(entry)
            self._counts[scope]["total"] += 1
            if would_trip:
                self._counts[scope]["would_trip"] += 1

    def report(self) -> dict[str, Any]:
        """Return a summary of shadow-mode findings.

        Includes per-scope trip rates, total evaluations, and the most
        recent would-trip reasons.
        """
        with self._lock:
            total = sum(c["total"] for c in self._counts.values())
            trips = sum(c["would_trip"] for c in self._counts.values())
            overall_rate = (trips / total * 100) if total > 0 else 0.0
            per_scope = self._per_scope_summary()
            recent_trips = [e for e in self._entries[-50:] if e["would_trip"]]
            return {
                "total_evaluations": total,
                "total_would_trip": trips,
                "overall_trip_rate_pct": round(overall_rate, 2),
                "per_scope": per_scope,
                "recent_trips": recent_trips,
            }

    def _per_scope_summary(self) -> dict[str, Any]:
        """Build per-scope trip rate summary."""
        per_scope: dict[str, Any] = {}
        for scope, counts in self._counts.items():
            sc_total = counts["total"]
            sc_trips = counts["would_trip"]
            rate = (sc_trips / sc_total * 100) if sc_total > 0 else 0.0
            per_scope[scope] = {
                "total_evaluations": sc_total,
                "would_trip_count": sc_trips,
                "trip_rate_pct": round(rate, 2),
            }
        return per_scope

    def reset(self) -> None:
        """Clear all shadow-mode data."""
        with self._lock:
            self._entries.clear()
            self._counts.clear()
