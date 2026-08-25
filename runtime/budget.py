#!/usr/bin/env python3
"""Token/cost budget governance for aiZee."""

from __future__ import annotations

import contextlib
import json
import logging
import os
import tempfile
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Literal

Period = Literal["session", "hourly", "daily", "weekly", "monthly"]
ExceedAction = Literal["warn", "fallback", "block"]

ALLOWED_PERIODS: set[Period] = {"session", "hourly", "daily", "weekly", "monthly"}
ALLOWED_EXCEED: set[ExceedAction] = {"warn", "fallback", "block"}

ALERT_THRESHOLD: float = 0.8  # 80% utilization triggers ALERT
WINDOW_PERIODS: set[str] = {"hourly", "daily", "weekly", "monthly"}

_logger = logging.getLogger(__name__)


class BudgetAction(str, Enum):
    """Action to take when a budget window threshold is crossed."""

    ALERT = "alert"   # Log + webhook + continue
    REJECT = "reject"  # Block + raise BudgetExceededError
    WARN = "warn"     # Log warning + continue


class BudgetTargetScope(str, Enum):
    """Scope at which a budget window applies."""

    SESSION = "session"
    AGENT = "agent"
    GLOBAL = "global"


@dataclass
class BudgetWindow:
    """Time-scoped budget tracking window with cumulative spend."""

    window_id: str
    scope: BudgetTargetScope
    scope_id: str  # session ID, agent ID, or "global"
    period: str  # "hourly", "daily", "weekly", "monthly"
    start_time: float
    end_time: float
    spend: float = 0.0  # cumulative spend in this window
    limit: float = 0.0  # budget limit for this window
    action: BudgetAction = BudgetAction.WARN
    is_active: bool = True

    @property
    def remaining(self) -> float:
        return max(0.0, self.limit - self.spend)

    @property
    def utilization(self) -> float:
        if self.limit <= 0:
            return 0.0
        return self.spend / self.limit

    @property
    def is_exceeded(self) -> bool:
        return self.spend >= self.limit and self.limit > 0


def _period_seconds(period: str) -> float:
    """Return the duration in seconds for a window period."""
    if period == "hourly":
        return 3600.0
    if period == "daily":
        return 86400.0
    if period == "weekly":
        return 604800.0
    if period == "monthly":
        return 2592000.0  # 30 days
    return 86400.0


class BudgetWindowManager:
    """Manages time-scoped budget windows with ALERT/REJECT enforcement.

    Tracks cumulative spend per window and enforces budget limits via
    pre-action checks (``check_budget_limit``) and post-action cost
    recording (``on_complete``). Windows can be backfilled from the audit
    log on restart and policies are lazily refreshed when stale.
    """

    def __init__(self) -> None:
        self._windows: dict[str, BudgetWindow] = {}
        self._alert_callbacks: list[Callable[[BudgetWindow], None]] = []
        self._last_policy_refresh: float = time.time()
        self._lock = threading.RLock()

    def register_window(self, window: BudgetWindow) -> None:
        """Register a budget window for tracking."""
        with self._lock:
            self._windows[window.window_id] = window

    def _matching_windows(
        self, scope: BudgetTargetScope, scope_id: str
    ) -> list[BudgetWindow]:
        """Return active windows matching the given scope and scope_id."""
        now = time.time()
        result: list[BudgetWindow] = []
        for w in self._windows.values():
            if not w.is_active:
                continue
            if w.scope != scope:
                continue
            if w.scope_id != scope_id:
                continue
            # Expire windows whose end_time has passed
            if w.end_time <= now:
                w.is_active = False
                continue
            result.append(w)
        return result

    def check_budget_limit(
        self, scope: BudgetTargetScope, scope_id: str, amount: float
    ) -> BudgetAction:
        """Pre-action check: returns the action to take for a projected spend.

        - Returns ``REJECT`` if any matching window would be exceeded and its
          action is ``REJECT``.
        - Returns ``ALERT`` if any matching window is at/above the alert
          threshold (80% by default) or already exceeded with action ``ALERT``.
        - Returns ``WARN`` otherwise.
        """
        with self._lock:
            windows = self._matching_windows(scope, scope_id)
            if not windows:
                return BudgetAction.WARN

            action = BudgetAction.WARN
            for w in windows:
                projected = w.spend + amount
                projected_util = projected / w.limit if w.limit > 0 else 0.0
                if projected >= w.limit and w.limit > 0:
                    if w.action == BudgetAction.REJECT:
                        return BudgetAction.REJECT
                    if w.action == BudgetAction.ALERT:
                        action = BudgetAction.ALERT
                elif projected_util >= ALERT_THRESHOLD and w.limit > 0:
                    if w.action in (BudgetAction.ALERT, BudgetAction.REJECT):
                        action = BudgetAction.ALERT
            return action

    def check_escalation(
        self,
        scope: BudgetTargetScope,
        scope_id: str,
        is_root: bool = True,
    ) -> Any | None:
        """Check if budget utilization has crossed an escalation stage.

        Uses :mod:`runtime.budget_escalation` to compute multi-stage
        escalation directives. Returns an ``EscalationDirective`` if a
        band has been crossed, or ``None`` if utilization is below the
        first band.
        """
        from runtime.budget_escalation import compute_escalation

        with self._lock:
            windows = self._matching_windows(scope, scope_id)
            if not windows:
                return None
            # Use the window with the highest utilization
            best_window = max(
                windows,
                key=lambda w: w.utilization if w.limit > 0 else 0.0,
            )
            if best_window.limit <= 0:
                return None
            return compute_escalation(
                spend=best_window.spend,
                limit=best_window.limit,
                is_root=is_root,
            )

    def should_stop_subagent(
        self,
        scope: BudgetTargetScope,
        scope_id: str,
    ) -> bool:
        """Check if a subagent should be force-stopped (reserve reached).

        Uses :mod:`runtime.budget_escalation` to check the subagent
        reserve fraction.
        """
        from runtime.budget_escalation import should_stop_subagent as _check

        with self._lock:
            windows = self._matching_windows(scope, scope_id)
            if not windows:
                return False
            best_window = max(
                windows,
                key=lambda w: w.utilization if w.limit > 0 else 0.0,
            )
            if best_window.limit <= 0:
                return False
            return _check(
                spend=best_window.spend,
                limit=best_window.limit,
            )

    def on_complete(
        self, scope: BudgetTargetScope, scope_id: str, actual_cost: float
    ) -> None:
        """Post-action callback: records actual cost from execution.

        Fires alert callbacks for any window that newly crosses a threshold
        or becomes exceeded after recording the cost.
        """
        with self._lock:
            windows = self._matching_windows(scope, scope_id)
            for w in windows:
                was_exceeded = w.is_exceeded
                prev_util = w.utilization
                w.spend += actual_cost
                now_exceeded = w.is_exceeded
                curr_util = w.utilization
                # Fire alert if newly exceeded or crossed the alert threshold
                crossed_threshold = (
                    prev_util < ALERT_THRESHOLD <= curr_util
                    or (not was_exceeded and now_exceeded)
                )
                if crossed_threshold:
                    self._fire_alerts(w)
            self._last_policy_refresh = time.time()

    def _fire_alerts(self, window: BudgetWindow) -> None:
        """Invoke registered alert callbacks for a window."""
        for cb in self._alert_callbacks:
            try:
                cb(window)
            except Exception:
                _logger.exception("Alert callback failed for window %s", window.window_id)

    def backfill_from_audit(self, audit_entries: list[dict[str, Any]]) -> None:
        """Reconstruct windows from audit log on restart.

        Each audit entry is expected to contain ``scope``, ``scope_id``,
        ``cost``, and ``timestamp`` keys. Windows are matched by scope +
        scope_id + period, and spend is accumulated for entries falling
        within the window's time range.
        """
        with self._lock:
            for entry in audit_entries:
                scope_str = entry.get("scope")
                scope_id = entry.get("scope_id", "")
                cost = float(entry.get("cost", 0.0))
                ts = float(entry.get("timestamp", 0.0))
                if not scope_str:
                    continue
                try:
                    scope = BudgetTargetScope(scope_str)
                except ValueError:
                    continue
                for w in self._windows.values():
                    if w.scope != scope or w.scope_id != scope_id:
                        continue
                    if w.start_time <= ts <= w.end_time:
                        w.spend += cost

    def register_alert_callback(self, cb: Callable[[BudgetWindow], None]) -> None:
        """Register a callback invoked when a window crosses a threshold."""
        with self._lock:
            self._alert_callbacks.append(cb)

    def get_active_windows(self) -> list[BudgetWindow]:
        """Return all currently active windows (not expired)."""
        with self._lock:
            now = time.time()
            active: list[BudgetWindow] = []
            for w in self._windows.values():
                if w.is_active and w.end_time > now:
                    active.append(w)
            return active

    def maybe_refresh_policies(self, stale_threshold: float = 300.0) -> bool:
        """Lazy policy refresh — only reload when stale (5 min default).

        Returns ``True`` if a refresh was performed, ``False`` if policies
        were still fresh.
        """
        with self._lock:
            now = time.time()
            if now - self._last_policy_refresh >= stale_threshold:
                self._last_policy_refresh = now
                return True
            return False


def make_window(
    scope: BudgetTargetScope,
    scope_id: str,
    period: str = "daily",
    limit: float = 0.0,
    action: BudgetAction = BudgetAction.WARN,
    window_id: str | None = None,
) -> BudgetWindow:
    """Helper to construct a ``BudgetWindow`` with computed time bounds."""
    now = time.time()
    duration = _period_seconds(period)
    return BudgetWindow(
        window_id=window_id or str(uuid.uuid4()),
        scope=scope,
        scope_id=scope_id,
        period=period,
        start_time=now,
        end_time=now + duration,
        spend=0.0,
        limit=limit,
        action=action,
        is_active=True,
    )


@dataclass
class Budget:
    max_tokens: int | None = None
    max_cost_usd: float | None = None
    max_calls: int | None = None
    period: Period = "session"
    on_exceed: ExceedAction = "block"
    fallback_model: str | None = None
    rollout_max_tokens: int | None = None
    rollout_reminder_threshold: float | None = None
    token_weight_input: float = 1.0
    token_weight_output: float = 1.0
    finalization_reserve: float = 0.0  # Fraction of budget reserved for final response

    def __post_init__(self) -> None:
        if self.period not in ALLOWED_PERIODS:
            self.period = "session"
        if self.on_exceed not in ALLOWED_EXCEED:
            self.on_exceed = "block"
        if self.finalization_reserve < 0 or self.finalization_reserve > 0.5:
            self.finalization_reserve = 0.0

    @property
    def effective_max_tokens(self) -> int | None:
        """Max tokens minus the finalization reserve."""
        if self.max_tokens is None:
            return None
        return int(self.max_tokens * (1.0 - self.finalization_reserve))

    @property
    def effective_max_cost(self) -> float | None:
        """Max cost minus the finalization reserve."""
        if self.max_cost_usd is None:
            return None
        return self.max_cost_usd * (1.0 - self.finalization_reserve)


class BudgetManager:
    """Tracks spend and enforces budgets across scopes."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.state_file = root / "state" / "budget.json"
        self.budgets: dict[str, Budget] = {}
        self.usage: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._dirty = False
        self.window_manager: BudgetWindowManager | None = None
        self._load()

    def _default_budgets(self) -> dict[str, Budget]:
        return {
            "global": Budget(max_tokens=1_000_000, max_cost_usd=50.0, period="daily"),
            "session": Budget(max_tokens=100_000, max_cost_usd=5.0),
        }

    def _load(self) -> None:
        if not self.state_file.exists():
            self.budgets = self._default_budgets()
            self._dirty = True
            return
        from runtime.crypto import decrypt_file

        try:
            data = json.loads(decrypt_file(self.state_file))
        except (ValueError, json.JSONDecodeError) as exc:
            # Corrupted or undecryptable state (e.g. encryption key rotated).
            # Quarantine the bad file and fall back to defaults so the OS
            # stays usable instead of crashing every CLI command.
            import logging

            quarantine = self.state_file.with_suffix(".json.corrupt.bak")
            with contextlib.suppress(OSError):
                self.state_file.replace(quarantine)
            logging.getLogger(__name__).warning(
                "budget.json unreadable (%s); quarantined to %s, using defaults",
                exc, quarantine,
            )
            self.budgets = self._default_budgets()
            self._dirty = True
            return
        self.usage = data.get("usage", {})
        for k, v in data.get("budgets", {}).items():
            self.budgets[k] = Budget(**v)

    def save(self) -> None:
        with self._lock:
            if not self._dirty:
                return
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            payload = json.dumps(
                {"budgets": {k: asdict(v) for k, v in self.budgets.items()}, "usage": self.usage},
                indent=2,
            )
            from runtime.crypto import encrypt_bytes

            encrypted = encrypt_bytes(payload.encode("utf-8"))
            tmp_fd, tmp_path = tempfile.mkstemp(dir=self.state_file.parent, suffix=".json.tmp")
            try:
                with os.fdopen(tmp_fd, "wb") as f:
                    f.write(encrypted)
                os.replace(tmp_path, self.state_file)
                self._dirty = False
            except Exception as exc:
                _logger.debug("budget state save failed: %s", exc, exc_info=True)
                with contextlib.suppress(OSError):
                    os.remove(tmp_path)
                raise

    def set_budget(self, scope: str, budget: Budget) -> None:
        with self._lock:
            self.budgets[scope] = budget
            self._dirty = True

    def _period_key(
        self, scope: str, budget: Budget, now: datetime, session_id: str | None = None
    ) -> str:
        if budget.period == "session" and session_id is not None:
            return session_id
        if budget.period == "session":
            return self.usage.get(scope, {}).get("session_id") or uuid.uuid4().hex
        if budget.period == "hourly":
            return now.strftime("%Y-%m-%d-%H")
        if budget.period == "daily":
            return now.strftime("%Y-%m-%d")
        if budget.period == "weekly":
            return now.strftime("%Y-W%W")
        if budget.period == "monthly":
            return now.strftime("%Y-%m")
        return "session"

    def _reset_if_needed(
        self, scope: str, budget: Budget, session_id: str | None = None
    ) -> None:
        now = datetime.now(timezone.utc)
        current_pid = os.getpid()
        u = self.usage.setdefault(scope, {"tokens": 0, "cost": 0, "calls": 0})
        current_key = self._period_key(scope, budget, now, session_id)

        if budget.period == "session":
            stored_pid = u.get("process_id")
            stored_sid = u.get("session_id")
            if stored_pid != current_pid or stored_sid != current_key:
                u.update(
                    {
                        "tokens": 0,
                        "cost": 0,
                        "calls": 0,
                        "session_id": current_key,
                        "process_id": current_pid,
                        "period_key": current_key,
                    }
                )
                self._dirty = True
            else:
                u.setdefault("period_key", current_key)
        else:
            if u.get("period_key") != current_key:
                u.update(
                    {
                        "tokens": 0,
                        "cost": 0,
                        "calls": 0,
                        "period_key": current_key,
                        "session_id": session_id or "",
                        "process_id": current_pid,
                    }
                )
                self._dirty = True

    def _weighted_tokens(
        self,
        budget: Budget,
        tokens: int,
        token_weight: float | None,
        input_tokens: int | None,
        output_tokens: int | None,
    ) -> int:
        if input_tokens is not None and output_tokens is not None:
            return int(input_tokens * budget.token_weight_input + output_tokens * budget.token_weight_output)
        if token_weight is not None:
            return int(tokens * token_weight)
        return tokens

    def _rollout_reminder(
        self,
        usage_tokens: int,
        projected_tokens: int,
        max_tokens: int | None,
        threshold: float | None,
    ) -> str | None:
        if not max_tokens or threshold is None:
            return None
        threshold_tokens = threshold * max_tokens
        if usage_tokens < threshold_tokens <= projected_tokens:
            return f"Rollout token usage at {threshold:.0%} of {max_tokens}"
        return None

    def check_rollout(
        self,
        rollout_id: str,
        tokens: int = 0,
        cost: float = 0.0,
        dry_run: bool = False,
        budget: Budget | None = None,
    ) -> dict[str, Any]:
        """Track usage per rollout and enforce rollout_max_tokens."""
        with self._lock:
            key = f"rollout:{rollout_id}"
            u = self.usage.setdefault(key, {"tokens": 0, "cost": 0, "calls": 0})
            projected_tokens = u["tokens"] + tokens
            projected_cost = u["cost"] + cost
            max_tokens = budget.rollout_max_tokens if budget else None
            threshold = budget.rollout_reminder_threshold if budget else None

            if max_tokens and projected_tokens >= max_tokens:
                return {
                    "ok": False,
                    "reason": "Rollout budget exceeded: tokens",
                    "action": "block",
                    "rollout_id": rollout_id,
                    "reminder": None,
                }

            reminder = self._rollout_reminder(u["tokens"], projected_tokens, max_tokens, threshold)
            if not dry_run:
                u.update({"tokens": projected_tokens, "cost": projected_cost, "calls": 0})
                self._dirty = True

            return {
                "ok": True,
                "reason": None,
                "action": "allow",
                "rollout_id": rollout_id,
                "reminder": reminder,
            }

    def check(
        self,
        scope: str,
        tokens: int = 0,
        cost: float = 0.0,
        calls: int = 0,
        dry_run: bool = False,
        rollout_id: str | None = None,
        token_weight: float | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Return {'ok': bool, 'reason': str | None, 'action': str}."""
        with self._lock:
            budget = self.budgets.get(scope)
            if not budget:
                return {"ok": True, "reason": None, "action": "allow"}

            self._reset_if_needed(scope, budget, session_id)

            u = self.usage[scope]
            effective_tokens = self._weighted_tokens(budget, tokens, token_weight, input_tokens, output_tokens)
            projected = {
                "tokens": u["tokens"] + effective_tokens,
                "cost": u["cost"] + cost,
                "calls": u["calls"] + calls,
            }

            exceeded = []
            if budget.effective_max_tokens and projected["tokens"] >= budget.effective_max_tokens:
                exceeded.append("tokens")
            if budget.effective_max_cost and projected["cost"] >= budget.effective_max_cost:
                exceeded.append("cost")
            if budget.max_calls and projected["calls"] >= budget.max_calls:
                exceeded.append("calls")

            # --- BudgetWindow integration (optional, backward-compatible) ---
            window_action: BudgetAction | None = None
            if self.window_manager is not None and self.window_manager.get_active_windows():
                w_scope = BudgetTargetScope.SESSION if scope == "session" else (
                    BudgetTargetScope.GLOBAL if scope == "global" else BudgetTargetScope.AGENT
                )
                w_action = self.window_manager.check_budget_limit(w_scope, scope, cost)
                if w_action == BudgetAction.REJECT:
                    return {
                        "ok": False,
                        "reason": "Budget window exceeded (REJECT)",
                        "action": "block",
                    }
                if w_action == BudgetAction.ALERT:
                    window_action = BudgetAction.ALERT

            if exceeded:
                if budget.on_exceed == "warn":
                    if not dry_run:
                        u.update(projected)
                        self._dirty = True
                    return {"ok": True, "reason": f"Budget exceeded: {exceeded}", "action": "warn"}
                if budget.on_exceed == "fallback" and budget.fallback_model:
                    if not dry_run:
                        u.update(projected)
                        self._dirty = True
                    return {
                        "ok": True,
                        "reason": f"Budget exceeded: {exceeded}",
                        "action": "fallback",
                        "fallback_model": budget.fallback_model,
                    }
                return {"ok": False, "reason": f"Budget exceeded: {exceeded}", "action": "block"}

            rollout_result: dict[str, Any] | None = None
            if rollout_id:
                rollout_result = self.check_rollout(rollout_id, effective_tokens, cost, dry_run, budget)
                if not rollout_result["ok"]:
                    return {
                        "ok": False,
                        "reason": rollout_result["reason"],
                        "action": "block",
                        "rollout": rollout_result,
                        "reminder": None,
                    }

            if not dry_run:
                u.update(projected)
                self._dirty = True
                if self.window_manager is not None and self.window_manager.get_active_windows():
                    w_scope = BudgetTargetScope.SESSION if scope == "session" else (
                        BudgetTargetScope.GLOBAL if scope == "global" else BudgetTargetScope.AGENT
                    )
                    self.window_manager.on_complete(w_scope, scope, cost)

            result: dict[str, Any] = {"ok": True, "reason": None, "action": "allow"}
            if window_action == BudgetAction.ALERT:
                result["action"] = "alert"
                result["reason"] = "Budget window approaching limit"
            if rollout_id and rollout_result is not None:
                result["rollout"] = rollout_result
                result["reminder"] = rollout_result["reminder"]
            return result

    def would_exceed(
        self,
        scope: str,
        estimated_cost: float = 0.0,
        estimated_tokens: int = 0,
        session_id: str | None = None,
    ) -> bool:
        """Check if adding estimated cost/tokens would exceed the budget.

        Accounts for the finalization reserve: the hard limit fires at
        ``effective_max_*`` (i.e., ``max * (1 - reserve)``), leaving the
        reserved fraction free for the agent's final response/summary.

        This enables graceful degradation — agents can check before
        starting a costly operation and return partial results instead
        of being cut off mid-task.
        """
        with self._lock:
            budget = self.budgets.get(scope)
            if not budget:
                return False
            self._reset_if_needed(scope, budget, session_id)
            u = self.usage[scope]
            eff_tokens = budget.effective_max_tokens
            eff_cost = budget.effective_max_cost
            if eff_tokens and (u["tokens"] + estimated_tokens) >= eff_tokens:
                return True
            return bool(eff_cost and (u["cost"] + estimated_cost) >= eff_cost)
