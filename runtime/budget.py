#!/usr/bin/env python3
"""Token/cost budget governance for AI Global OS."""

from __future__ import annotations

import json
import os
import tempfile
import threading
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

Period = Literal["session", "hourly", "daily", "weekly", "monthly"]
ExceedAction = Literal["warn", "fallback", "block"]

ALLOWED_PERIODS: set[Period] = {"session", "hourly", "daily", "weekly", "monthly"}
ALLOWED_EXCEED: set[ExceedAction] = {"warn", "fallback", "block"}


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

    def __post_init__(self) -> None:
        if self.period not in ALLOWED_PERIODS:
            self.period = "session"
        if self.on_exceed not in ALLOWED_EXCEED:
            self.on_exceed = "block"


class BudgetManager:
    """Tracks spend and enforces budgets across scopes."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.state_file = root / "state" / "budget.json"
        self.budgets: dict[str, Budget] = {}
        self.usage: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._dirty = False
        self._load()

    def _load(self) -> None:
        if self.state_file.exists():
            from runtime.crypto import decrypt_file

            data = json.loads(decrypt_file(self.state_file))
            self.usage = data.get("usage", {})
            for k, v in data.get("budgets", {}).items():
                self.budgets[k] = Budget(**v)
        else:
            self.budgets = {
                "global": Budget(max_tokens=1_000_000, max_cost_usd=50.0, period="daily"),
                "session": Budget(max_tokens=100_000, max_cost_usd=5.0),
            }
            self._dirty = True

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
            except Exception:
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
            if budget.max_tokens and projected["tokens"] >= budget.max_tokens:
                exceeded.append("tokens")
            if budget.max_cost_usd and projected["cost"] >= budget.max_cost_usd:
                exceeded.append("cost")
            if budget.max_calls and projected["calls"] >= budget.max_calls:
                exceeded.append("calls")

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

            result: dict[str, Any] = {"ok": True, "reason": None, "action": "allow"}
            if rollout_id:
                result["rollout"] = rollout_result
                result["reminder"] = rollout_result["reminder"]
            return result
