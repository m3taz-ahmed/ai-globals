#!/usr/bin/env python3
"""AI Global OS runtime kernel."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

import config

from .audit import AuditLogger
from .budget import BudgetManager
from .plugin import PluginManager
from .policy import PolicyEngine
from .workflow import WorkflowRunner

if TYPE_CHECKING:
    from memory.store import MemoryStore


class ActionSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str = Field(..., min_length=1)
    tokens: int = 0
    cost: float = 0.0


class WorkflowContextSchema(BaseModel):
    model_config = ConfigDict(extra="allow")


class Kernel:
    """Central runtime for AI Global OS."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or config.discover_root()
        self.policy = PolicyEngine(self.root)
        self.budget = BudgetManager(self.root)
        self.workflows = WorkflowRunner(self.root)
        self.audit = AuditLogger(self.root)
        self.plugins = PluginManager(self, self.root)

    def act(self, action_type: str, dry_run: bool = False, **kwargs: Any) -> dict[str, Any]:
        """Evaluate action through policy + budget gates."""
        try:
            action_data = ActionSchema(type=action_type, **kwargs).model_dump()
        except Exception as e:
            return {"ok": False, "error": f"Invalid action arguments: {e!s}"}

        decision = self.policy.can(action_data["type"], **action_data)
        if decision["decision"] == "deny":
            if not dry_run:
                self.audit.log("policy.denied", {"action": action_data["type"], "args": kwargs, "decision": decision})
            return {"ok": False, "error": f"Policy denied by {decision['rule']}", "decision": decision}

        if decision["decision"] == "ask" and not action_data.get("approved"):
            if not dry_run:
                self.audit.log("policy.asked", {"action": action_data["type"], "args": kwargs, "decision": decision})
            return {
                "ok": False,
                "error": "Action requires explicit approval (approved=True)",
                "requires_approval": True,
                "decision": decision,
            }

        budget_result = self.budget.check("session", action_data.get("tokens", 0), action_data.get("cost", 0.0), dry_run=dry_run)
        if not dry_run:
            self.budget.save()
            if not budget_result["ok"]:
                self.audit.log("budget.blocked", {"action": action_data["type"], "args": kwargs, "budget": budget_result})
            else:
                self.audit.log("action.allowed", {"action": action_data["type"], "args": kwargs, "decision": decision, "budget": budget_result})

        if not budget_result["ok"]:
            return {"ok": False, "error": budget_result["reason"], "budget": budget_result}

        return {
            "ok": True,
            "decision": decision,
            "budget": budget_result,
            "action": action_data["type"],
            "args": kwargs,
        }

    def run_workflow(self, workflow_id: str, context: dict[str, Any]) -> dict[str, Any]:
        try:
            valid_context = WorkflowContextSchema(**context).model_dump()
        except Exception as e:
            return {"ok": False, "error": f"Invalid workflow context: {e!s}"}
        return self.workflows.run(workflow_id, valid_context)

    def list_workflows(self) -> list[str]:
        return self.workflows.list_workflows()

    def load_plugins(self, memory: MemoryStore | None = None) -> None:
        """Load all enabled plugins and wire memory if available."""
        self.plugins.load_all(memory)

    def save(self) -> None:
        self.budget.save()

    def status(self) -> dict[str, Any]:
        return {
            "version": config.VERSION,
            "root": str(self.root),
            "workflows": self.list_workflows(),
            "budgets": list(self.budget.budgets.keys()),
            "rules": [r.name for r in self.policy.rules],
            "plugins": self.plugins.list_plugins(),
        }


if __name__ == "__main__":
    k = Kernel()
    print(json.dumps(k.status(), indent=2))
