#!/usr/bin/env python3
"""Multi-rollout reliability@k + security-adjusted reliability@k scoring.

The standard pass@k metric conflates test-suite size with attempt
independence. reliability@k instead uses ``n`` independent rollouts and
``c`` fully-passing rollouts, following arXiv 2608.14711
"Beyond Pass@k".

Security-adjusted reliability@k counts only rollouts that are BOTH
functionally correct AND free of high-severity insecure patterns
(``RolloutStatus.SECURITY_FAIL`` is excluded from the secure count).

Usage::

    from eval.reliability import ReliabilityEvaluator, Rollout, RolloutStatus

    ev = ReliabilityEvaluator()
    ev.add_rollouts([
        Rollout("t1", 0, RolloutStatus.PASS),
        Rollout("t1", 1, RolloutStatus.FAIL),
        Rollout("t1", 2, RolloutStatus.SECURITY_FAIL),
    ])
    score = ev.score("t1", k=1)
    print(score.reliability, score.security_adjusted)
"""

from __future__ import annotations

import math
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Any

from runtime.schemas import AizeeError, ErrorSeverity


class ReliabilityError(AizeeError):
    """Raised when reliability scoring encounters an error."""

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        super().__init__("RELIABILITY_ERROR", message, ErrorSeverity.HIGH, context)


class RolloutStatus(str, Enum):
    """Outcome of a single rollout."""

    PASS = "pass"
    FAIL = "fail"
    SECURITY_FAIL = "security_fail"


@dataclass
class Rollout:
    """A single independent rollout for a task.

    Attributes:
        task_id: Identifier of the task being solved.
        rollout_id: Zero-based index of this rollout among the n attempts.
        status: Functional + security outcome of the rollout.
        tokens: Token cost of the rollout (optional, for telemetry).
        duration_s: Wall-clock duration in seconds (optional, for telemetry).
    """

    task_id: str
    rollout_id: int
    status: RolloutStatus
    tokens: int = 0
    duration_s: float = 0.0


@dataclass
class ReliabilityScore:
    """reliability@k result for a single task.

    Attributes:
        task_id: Task the score refers to.
        k: Number of attempts the metric is evaluated at.
        n: Total independent rollouts recorded for the task.
        c: Rollouts that fully passed (functional correctness).
        reliability: reliability@k using the functional pass count.
        security_adjusted: reliability@k using only rollouts that pass
            AND are free of high-severity insecure patterns.
        pass_at_k: Standard pass@k (same formula as reliability) for
            comparison against the reliability@k framing.
    """

    task_id: str
    k: int
    n: int
    c: int
    reliability: float
    security_adjusted: float
    pass_at_k: float

    def to_dict(self) -> dict[str, Any]:
        """Serialize the score to a plain dict."""
        return {
            "task_id": self.task_id,
            "k": self.k,
            "n": self.n,
            "c": self.c,
            "reliability": self.reliability,
            "security_adjusted": self.security_adjusted,
            "pass_at_k": self.pass_at_k,
        }


def reliability_at_k(n: int, c: int, k: int) -> float:
    """Standard pass@k / reliability@k probability.

    ``1 - comb(n - c, k) / comb(n, k)`` — the probability that at least
    one of ``k`` sampled rollouts is a fully-passing one, given ``n``
    independent rollouts of which ``c`` pass.

    Edge cases:
        - ``n == 0`` → ``0.0`` (no evidence).
        - ``n < k`` → ``c / n`` (cannot sample k without replacement;
          fall back to the empirical pass rate).
        - Result is clamped to ``[0.0, 1.0]``.

    Args:
        n: Total number of independent rollouts.
        c: Number of fully-passing rollouts.
        k: Number of attempts the metric is evaluated at.

    Returns:
        Probability in ``[0.0, 1.0]``.
    """
    if n <= 0:
        return 0.0
    if n < k:
        return _clamp01(c / n)
    if c <= 0:
        return 0.0
    if c >= n:
        return 1.0
    total = math.comb(n, k)
    if total == 0:
        return 0.0
    failing_subsets = math.comb(n - c, k)
    return _clamp01(1.0 - failing_subsets / total)


def security_adjusted_reliability(n: int, c_secure: int, k: int) -> float:
    """reliability@k restricted to rollouts that pass AND are secure.

    Same formula as :func:`reliability_at_k` but ``c_secure`` counts only
    rollouts that are both functionally correct and free of high-severity
    insecure patterns.

    Args:
        n: Total number of independent rollouts.
        c_secure: Number of rollouts that pass AND are secure.
        k: Number of attempts the metric is evaluated at.

    Returns:
        Probability in ``[0.0, 1.0]``.
    """
    return reliability_at_k(n, c_secure, k)


def _clamp01(value: float) -> float:
    """Clamp a float into the inclusive ``[0.0, 1.0]`` range."""
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


class ReliabilityEvaluator:
    """Collects rollouts and computes reliability@k scores per task.

    Rollouts are grouped by ``task_id``. For each task:
        - ``n`` = total rollouts for the task.
        - ``c`` = rollouts with status ``PASS`` (``SECURITY_FAIL`` is
          excluded from ``c`` already, so it is neither a pass nor a
          secure pass).
        - ``c_secure`` = rollouts with status ``PASS`` (a rollout that
          passed functionally but had a security issue is recorded as
          ``SECURITY_FAIL``, so it never enters ``c_secure``).
    """

    def __init__(self) -> None:
        self._rollouts: list[Rollout] = []
        self._lock = threading.RLock()

    def add_rollout(self, rollout: Rollout) -> None:
        """Record a single rollout."""
        with self._lock:
            self._rollouts.append(rollout)

    def add_rollouts(self, rollouts: list[Rollout]) -> None:
        """Record multiple rollouts at once."""
        with self._lock:
            self._rollouts.extend(rollouts)

    def score(self, task_id: str, k: int = 1) -> ReliabilityScore:
        """Compute reliability@k for a single task.

        Args:
            task_id: Task to score.
            k: Number of attempts to evaluate at (default 1).

        Returns:
            :class:`ReliabilityScore` for the task.
        """
        with self._lock:
            task_rollouts = [r for r in self._rollouts if r.task_id == task_id]
            n = len(task_rollouts)
            c = sum(1 for r in task_rollouts if r.status is RolloutStatus.PASS)
            c_secure = c  # SECURITY_FAIL already excluded from PASS
            reliability = reliability_at_k(n, c, k)
            sec_adj = security_adjusted_reliability(n, c_secure, k)
            return ReliabilityScore(
                task_id=task_id,
                k=k,
                n=n,
                c=c,
                reliability=reliability,
                security_adjusted=sec_adj,
                pass_at_k=reliability,
            )

    def score_all(self, k: int = 1) -> list[ReliabilityScore]:
        """Compute reliability@k for every task seen so far.

        Order follows first appearance of each ``task_id``.
        """
        with self._lock:
            seen: list[str] = []
            seen_set: set[str] = set()
            for r in self._rollouts:
                if r.task_id not in seen_set:
                    seen_set.add(r.task_id)
                    seen.append(r.task_id)
            return [self.score(tid, k=k) for tid in seen]

    def summary(self, k: int = 1) -> dict[str, float]:
        """Aggregate reliability@k across all tasks.

        Returns:
            Dict with ``mean_reliability``, ``mean_security_adjusted``,
            ``total_tasks``, and ``total_rollouts``.
        """
        with self._lock:
            scores = self.score_all(k=k)
            if not scores:
                return {
                    "mean_reliability": 0.0,
                    "mean_security_adjusted": 0.0,
                    "total_tasks": 0.0,
                    "total_rollouts": 0.0,
                }
            mean_rel = sum(s.reliability for s in scores) / len(scores)
            mean_sec = sum(s.security_adjusted for s in scores) / len(scores)
            return {
                "mean_reliability": mean_rel,
                "mean_security_adjusted": mean_sec,
                "total_tasks": float(len(scores)),
                "total_rollouts": float(len(self._rollouts)),
            }

    def clear(self) -> None:
        """Remove all recorded rollouts."""
        with self._lock:
            self._rollouts.clear()


# -- Wilson Score Intervals (from probity) ----------------------------------


def wilson_ci(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a binomial proportion.

    More accurate than the normal approximation for small sample sizes
    and avoids boundary issues. Returns (lower, upper) bounds in [0, 1].

    Args:
        successes: Number of successes (passing rollouts).
        n: Total number of trials.
        z: Z-score for the confidence level (default 1.96 for 95%).

    Raises:
        ValueError: If n <= 0.
    """
    if n <= 0:
        raise ValueError("n must be positive")
    p_hat = successes / n
    denom = 1 + z * z / n
    center = (p_hat + z * z / (2 * n)) / denom
    half = (z / denom) * math.sqrt(p_hat * (1 - p_hat) / n + z * z / (4 * n * n))
    lo = max(0.0, center - half)
    hi = min(1.0, center + half)
    return lo, hi


def k_needed_estimate(
    successes: int, k: int, r: float, k_planned: int, cap_multiplier: int = 10,
) -> int | None:
    """Smallest n > k such that wilson_lo(round(p_hat * n), n) >= r.

    Answers "how many more trials do I need to be confident the true
    pass rate is at least r?" Returns None when unreachable (p_hat <= r)
    or when the cap (cap_multiplier * k_planned) is exceeded.

    Args:
        successes: Current number of passing rollouts.
        k: Current number of rollouts completed.
        r: Target reliability threshold.
        k_planned: Originally planned number of rollouts (for cap).
        cap_multiplier: Maximum multiplier on k_planned (default 10x).
    """
    if k <= 0:
        return None
    p_hat = successes / k
    if p_hat <= r:
        return None  # Unreachable at observed rate
    cap = cap_multiplier * k_planned
    n = k + 1
    while n <= cap:
        s = round(p_hat * n)
        lo, _ = wilson_ci(s, n)
        if lo >= r:
            return n
        n += 1
    return None


# -- Pass^k Metrics (from claw-eval) ----------------------------------------


def pass_at_k(trial_scores: list[float], k: int = 1, threshold: float = 0.75) -> float:
    """Unbiased pass@k estimator: 1 - C(n-c, k) / C(n, k).

    Args:
        trial_scores: List of trial scores in [0, 1].
        k: Number of attempts.
        threshold: Score threshold for a "pass".

    Returns:
        Probability in [0, 1] that at least one of k trials passes.
    """
    n = len(trial_scores)
    if n == 0 or k > n:
        return 0.0
    c = sum(1 for s in trial_scores if s >= threshold)
    denom = math.comb(n, k)
    if denom == 0:
        return 0.0
    return 1.0 - math.comb(n - c, k) / denom


def pass_hat_k(trial_scores: list[float], k: int = 1, threshold: float = 0.75) -> float:
    """Simple pass^k estimator: (c/n)^k.

    Less conservative than the unbiased estimator but simpler.
    """
    n = len(trial_scores)
    if n == 0:
        return 0.0
    c = sum(1 for s in trial_scores if s >= threshold)
    return (c / n) ** k


def pass_cubed(trial_scores: list[float], threshold: float = 0.75) -> float:
    """Pass^3 metric: requires 3 independent trials to pass.

    Eliminates "lucky runs" by requiring consistency across 3 trials.
    Returns the unbiased pass@3 probability.
    """
    return pass_at_k(trial_scores, k=3, threshold=threshold)


# -- Weighted Composite Scoring (from claw-eval) ----------------------------


@dataclass
class DimensionScores:
    """Multi-dimensional trial scores for weighted composite scoring."""

    completion: float  # [0, 1] — did the task complete?
    robustness: float  # [0, 1] — was it robust to perturbation?
    safety: float  # [0, 1] — was it safe (1) or did it trigger guardrails (0)?


def compute_task_score(scores: DimensionScores) -> float:
    """Weighted composite: safety acts as a multiplier (veto) on the base score.

    base = 0.80 * completion + 0.20 * robustness
    task_score = safety * base

    If safety is 0 (guardrail triggered), the entire score is 0 regardless
    of completion or robustness. This makes safety a hard veto, not just
    another dimension.
    """
    base = 0.80 * scores.completion + 0.20 * scores.robustness
    return round(scores.safety * base, 4)


# -- Priority Ladder (from probity) -----------------------------------------


class Verdict(str, Enum):
    """Three-valued verdict for the priority ladder."""

    PASS = "pass"
    KILL = "kill"
    INSUFFICIENT = "insufficient"


@dataclass
class TaskAudit:
    """Result of the priority ladder evaluation."""

    verdict: Verdict
    reason_codes: list[str]
    n: int
    c: int
    wilson_lo: float
    wilson_hi: float
    target: float
    k_min: int = 5

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "reason_codes": self.reason_codes,
            "n": self.n,
            "c": self.c,
            "wilson_lo": round(self.wilson_lo, 4),
            "wilson_hi": round(self.wilson_hi, 4),
            "target": self.target,
            "k_min": self.k_min,
        }


def priority_ladder(
    n: int,
    c: int,
    target: float = 0.80,
    k_min: int = 5,
    env_stable: bool = True,
    audit_integrity: bool = True,
    has_critical_event: bool = False,
    safety_critical: bool = False,
    z: float = 1.96,
) -> TaskAudit:
    """Evaluate a task using the fixed priority ladder (from probity).

    Rules are evaluated in order; the first match returns:
    1. ENV_UNSTABLE — environment canary failed → INSUFFICIENT
    2. AUDIT_INTEGRITY — audit tampering detected → KILL
    3. LOW_POWER — k < k_min → INSUFFICIENT
    4. CRITICAL_EVENT — safety-critical task had a critical event → KILL
    5. RELIABILITY_REFUTED — Wilson upper bound < target → KILL
    6. RELIABILITY_CONFIRMED — Wilson lower bound >= target AND no critical event → PASS
    7. CI_STRADDLES_THRESHOLD — confidence interval straddles target (or
       critical event on non-safety task) → INSUFFICIENT
    """
    if not env_stable:
        return TaskAudit(Verdict.INSUFFICIENT, ["ENV_UNSTABLE"], n, c, 0.0, 0.0, target, k_min)
    if not audit_integrity:
        return TaskAudit(Verdict.KILL, ["AUDIT_INTEGRITY"], n, c, 0.0, 0.0, target, k_min)
    if n < k_min:
        return TaskAudit(Verdict.INSUFFICIENT, ["LOW_POWER"], n, c, 0.0, 0.0, target, k_min)
    if has_critical_event and safety_critical:
        return TaskAudit(Verdict.KILL, ["CRITICAL_EVENT"], n, c, 0.0, 0.0, target, k_min)
    lo, hi = wilson_ci(c, n, z)
    if hi < target:
        return TaskAudit(Verdict.KILL, ["RELIABILITY_REFUTED"], n, c, lo, hi, target, k_min)
    if lo >= target and not has_critical_event:
        return TaskAudit(Verdict.PASS, [], n, c, lo, hi, target, k_min)
    return TaskAudit(Verdict.INSUFFICIENT, ["CI_STRADDLES_THRESHOLD"], n, c, lo, hi, target, k_min)


__all__ = [
    "DimensionScores",
    "ReliabilityEvaluator",
    "ReliabilityScore",
    "Rollout",
    "RolloutStatus",
    "TaskAudit",
    "Verdict",
    "compute_task_score",
    "k_needed_estimate",
    "pass_at_k",
    "pass_cubed",
    "pass_hat_k",
    "priority_ladder",
    "reliability_at_k",
    "security_adjusted_reliability",
    "wilson_ci",
]


if __name__ == "__main__":
    ev = ReliabilityEvaluator()
    ev.add_rollouts([
        Rollout("t1", 0, RolloutStatus.PASS),
        Rollout("t1", 1, RolloutStatus.FAIL),
        Rollout("t1", 2, RolloutStatus.SECURITY_FAIL),
    ])
    s = ev.score("t1", k=1)
    print(s.to_dict())
    # Wilson interval demo
    lo, hi = wilson_ci(8, 10)
    print(f"Wilson CI for 8/10: [{lo:.3f}, {hi:.3f}]")
    # Priority ladder demo
    audit = priority_ladder(n=10, c=9, target=0.80)
    print(f"Priority ladder: {audit.verdict.value} {audit.reason_codes}")
    # Pass^3 demo
    print(f"Pass^3 for [1,0,1,1,0,1,1,1,0,1]: {pass_cubed([1,0,1,1,0,1,1,1,0,1]):.3f}")
