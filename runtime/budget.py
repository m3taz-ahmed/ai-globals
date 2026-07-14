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
        self._lock = threading.Lock()
        self._load()

    def _load(self) -> None:
        if self.state_file.exists():
            data = json.loads(self.state_file.read_text(encoding="utf-8"))
            self.usage = data.get("usage", {})
            for k, v in data.get("budgets", {}).items():
                self.budgets[k] = Budget(**v)
        else:
            self.budgets = {
                "global": Budget(max_tokens=1_000_000, max_cost_usd=50.0, period="daily"),
                "session": Budget(max_tokens=100_000, max_cost_usd=5.0),
            }

    def save(self) -> None:
        with self._lock:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            payload = json.dumps(
                {"budgets": {k: asdict(v) for k, v in self.budgets.items()}, "usage": self.usage},
                indent=2,
            )
            tmp_fd, tmp_path = tempfile.mkstemp(dir=self.state_file.parent, suffix=".json.tmp")
            try:
                with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                    f.write(payload)
                os.replace(tmp_path, self.state_file)
            except Exception:
                os.remove(tmp_path)
                raise

    def set_budget(self, scope: str, budget: Budget) -> None:
        with self._lock:
            self.budgets[scope] = budget

    def _period_key(self, scope: str, budget: Budget, now: datetime) -> str:
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

    def _reset_if_needed(self, scope: str, budget: Budget) -> None:
        now = datetime.now(timezone.utc)
        current_pid = os.getpid()
        u = self.usage.setdefault(scope, {"tokens": 0, "cost": 0, "calls": 0})
        current_key = self._period_key(scope, budget, now)

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
                        "session_id": "",
                        "process_id": current_pid,
                    }
                )

    def check(self, scope: str, tokens: int = 0, cost: float = 0.0, calls: int = 0, dry_run: bool = False) -> dict[str, Any]:
        """Return {'ok': bool, 'reason': str | None, 'action': str}."""
        with self._lock:
            budget = self.budgets.get(scope)
            if not budget:
                return {"ok": True, "reason": None, "action": "allow"}

            self._reset_if_needed(scope, budget)

            u = self.usage[scope]
            projected = {
                "tokens": u["tokens"] + tokens,
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
                    return {"ok": True, "reason": f"Budget exceeded: {exceeded}", "action": "warn"}
                if budget.on_exceed == "fallback" and budget.fallback_model:
                    if not dry_run:
                        u.update(projected)
                    return {
                        "ok": True,
                        "reason": f"Budget exceeded: {exceeded}",
                        "action": "fallback",
                        "fallback_model": budget.fallback_model,
                    }
                return {"ok": False, "reason": f"Budget exceeded: {exceeded}", "action": "block"}

            if not dry_run:
                u.update(projected)
            return {"ok": True, "reason": None, "action": "allow"}
