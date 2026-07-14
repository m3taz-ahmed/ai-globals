#!/usr/bin/env python3
"""Token/cost budget governance for AI Global OS."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

Scope = Literal["global", "session", "task", "agent", "project"]


@dataclass
class Budget:
    max_tokens: int | None = None
    max_cost_usd: float | None = None
    max_calls: int | None = None
    period: str = "session"
    on_exceed: Literal["warn", "fallback", "block"] = "block"
    fallback_model: str | None = None


class BudgetManager:
    """Tracks spend and enforces budgets across scopes."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.state_file = root / "state" / "budget.json"
        self.budgets: dict[str, Budget] = {}
        self.usage: dict[str, dict[str, Any]] = {}
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
                "session": Budget(max_tokens=100_000, max_cost_usd=5.0, period="session"),
            }

    def save(self) -> None:
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
        self.budgets[scope] = budget

    def check(self, scope: str, tokens: int = 0, cost: float = 0.0, calls: int = 0) -> dict[str, Any]:
        """Return {'ok': bool, 'reason': str | None, 'action': str}."""
        budget = self.budgets.get(scope)
        if not budget:
            return {"ok": True, "reason": None, "action": "allow"}

        u = self.usage.setdefault(scope, {"tokens": 0, "cost": 0, "calls": 0})
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
                u.update(projected)
                return {"ok": True, "reason": f"Budget exceeded: {exceeded}", "action": "warn"}
            if budget.on_exceed == "fallback" and budget.fallback_model:
                u.update(projected)
                return {
                    "ok": True,
                    "reason": f"Budget exceeded: {exceeded}",
                    "action": "fallback",
                    "fallback_model": budget.fallback_model,
                }
            return {"ok": False, "reason": f"Budget exceeded: {exceeded}", "action": "block"}

        u.update(projected)
        return {"ok": True, "reason": None, "action": "allow"}
