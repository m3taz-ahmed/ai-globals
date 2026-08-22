#!/usr/bin/env python3
"""Budget anomaly detection (from agent-governance-toolkit).

Detects unusual budget consumption patterns using statistical analysis.
Triggers alerts when spending deviates significantly from baseline.

Usage::

    from runtime.budget_anomaly import BudgetAnomalyDetector

    detector = BudgetAnomalyDetector(baseline_window=100, threshold=3.0)
    detector.record(50)
    detector.record(55)
    anomaly = detector.check(500)  # Spike
"""

from __future__ import annotations

import math
import time
import uuid
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from runtime.budget import BudgetAction, BudgetTargetScope, BudgetWindow


@dataclass
class BudgetAnomalyDetector:
    """Detect budget consumption anomalies using z-score analysis.

    Maintains a sliding window of historical spending and flags
    values that deviate more than `threshold` standard deviations.
    """

    baseline_window: int = 100
    threshold: float = 3.0  # Standard deviations
    _history: deque[float] = field(default_factory=lambda: deque(maxlen=100))

    def __post_init__(self) -> None:
        self._history = deque(maxlen=self.baseline_window)

    def record(self, value: float) -> None:
        """Record a spending value."""
        self._history.append(value)

    @property
    def _stats(self) -> tuple[float, float]:
        """Return (mean, std_dev) of history."""
        if len(self._history) < 2:
            return 0.0, 0.0
        values = list(self._history)
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        return mean, math.sqrt(variance)

    def check(self, value: float) -> dict[str, Any]:
        """Check if a value is anomalous.

        Returns dict with:
        - is_anomaly: bool
        - z_score: float
        - mean: float
        - std_dev: float
        """
        if len(self._history) < 2:
            return {"is_anomaly": False, "z_score": 0.0, "mean": 0.0, "std_dev": 0.0}
        mean, std = self._stats
        if std == 0:
            return {"is_anomaly": value != mean, "z_score": 0.0, "mean": mean, "std_dev": 0.0}
        z = abs(value - mean) / std
        return {
            "is_anomaly": z > self.threshold,
            "z_score": z,
            "mean": mean,
            "std_dev": std,
        }

    def is_anomaly(self, value: float) -> bool:
        """Quick check if value is anomalous."""
        return bool(self.check(value)["is_anomaly"])


# ---------------------------------------------------------------------------
# Budget alerts (webhook-style, from MLflow gateway pattern)
# ---------------------------------------------------------------------------


@dataclass
class BudgetAlert:
    """Alert fired when a budget window crosses a utilization threshold."""

    alert_id: str
    window_id: str
    scope: BudgetTargetScope
    scope_id: str
    utilization: float  # 0.0-1.0
    threshold: float  # e.g., 0.8 for 80%
    message: str
    timestamp: float
    action_taken: BudgetAction


class BudgetAlerter:
    """Webhook-style alert system for budget threshold crossings.

    Checks window utilization against configured thresholds (50%, 80%,
    90%, 100% by default) and dispatches ``BudgetAlert`` objects to
    registered webhook callbacks.
    """

    def __init__(self) -> None:
        self._webhooks: list[Callable[[BudgetAlert], None]] = []
        self._thresholds: list[float] = [0.5, 0.8, 0.9, 1.0]  # 50%, 80%, 90%, 100%
        self._fired: set[tuple[str, float]] = set()

    def register_webhook(self, cb: Callable[[BudgetAlert], None]) -> None:
        """Register a webhook callback invoked for each alert."""
        self._webhooks.append(cb)

    def check_thresholds(self, window: BudgetWindow) -> list[BudgetAlert]:
        """Check if window utilization crosses any threshold.

        Returns a list of ``BudgetAlert`` objects for each newly-crossed
        threshold. Each threshold fires at most once per window to avoid
        duplicate alerts.
        """
        alerts: list[BudgetAlert] = []
        util = window.utilization
        for threshold in self._thresholds:
            if util >= threshold:
                key = (window.window_id, threshold)
                if key in self._fired:
                    continue
                self._fired.add(key)
                alerts.append(
                    BudgetAlert(
                        alert_id=str(uuid.uuid4()),
                        window_id=window.window_id,
                        scope=window.scope,
                        scope_id=window.scope_id,
                        utilization=util,
                        threshold=threshold,
                        message=(
                            f"Budget window {window.window_id} "
                            f"reached {threshold:.0%} utilization "
                            f"(spend={window.spend:.4f}, limit={window.limit:.4f})"
                        ),
                        timestamp=time.time(),
                        action_taken=window.action,
                    )
                )
        return alerts

    def send_alerts(self, alerts: list[BudgetAlert]) -> None:
        """Dispatch alerts to all registered webhooks."""
        for alert in alerts:
            for cb in self._webhooks:
                cb(alert)


if __name__ == "__main__":
    detector = BudgetAnomalyDetector(baseline_window=10, threshold=2.0)
    for v in [50, 55, 48, 52, 51, 49, 53, 50, 54, 51]:
        detector.record(v)
    print(f"Normal: {detector.check(52)}")
    print(f"Anomaly: {detector.check(500)}")
