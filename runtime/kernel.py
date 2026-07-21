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
from .chat import ChatSession
from .orchestrator import AgentPool
from .persona import PersonaDetector
from .plugin import PluginManager
from .policy import PolicyEngine
from .saga import Saga, SagaOrchestrator, SagaStep
from .tech_stack import detect_stack
from .telemetry import TelemetryCollector
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

    def __init__(self, root: Path | None = None, project_root: Path | None = None) -> None:
        self.root = root or config.discover_root()
        self.project_root = project_root or root or config.discover_project_root()
        self.policy = PolicyEngine(self.root, self.project_root)
        self.budget = BudgetManager(self.project_root)
        self.workflows = WorkflowRunner(self.project_root, self.root)
        self.saga = self._build_saga_orchestrator()
        self.telemetry = self._build_telemetry_collector()
        self.chat = ChatSession(self.project_root)
        self.pool = AgentPool(self.root)
        self.persona = PersonaDetector()
        self.audit = AuditLogger(self.project_root)
        self.plugins = PluginManager(self, self.root)

    def _build_saga_orchestrator(self) -> SagaOrchestrator:
        return SagaOrchestrator(self.project_root)

    def _build_telemetry_collector(self) -> TelemetryCollector:
        return TelemetryCollector(self.project_root)

    def detect_persona(self, text: str) -> dict[str, Any]:
        """Detect the best persona for a user prompt."""
        return self.persona.detect(text)

    def _auto_persona(self, kwargs: dict[str, Any]) -> None:
        """Inject a persona into kwargs if missing and a text prompt is present."""
        if "persona" in kwargs:
            return
        text = kwargs.get("message") or kwargs.get("content") or kwargs.get("query") or kwargs.get("request")
        if isinstance(text, str) and text.strip():
            kwargs["persona"] = self.persona.detect(text)["persona"]

    def act(self, action_type: str, dry_run: bool = False, **kwargs: Any) -> dict[str, Any]:
        """Evaluate action through policy + budget gates."""
        self._auto_persona(kwargs)
        try:
            action_data = ActionSchema(type=action_type, **kwargs).model_dump()
        except Exception as e:
            return {"ok": False, "error": f"Invalid action arguments: {e!s}"}

        decision = self.policy.can(action_data["type"], **action_data)
        if decision["decision"] == "deny":
            if not dry_run:
                self.audit.log("policy.denied", {"action": action_data["type"], "args": kwargs, "decision": decision})
            self.telemetry.record(
                event_type="action",
                action=action_data["type"],
                status="policy_denied",
                tokens=action_data.get("tokens", 0),
                cost=action_data.get("cost", 0.0),
                metadata={"decision": decision, "dry_run": dry_run, "args": kwargs},
            )
            return {"ok": False, "error": f"Policy denied by {decision['rule']}", "decision": decision}

        if decision["decision"] == "ask" and not action_data.get("approved"):
            if not dry_run:
                self.audit.log("policy.asked", {"action": action_data["type"], "args": kwargs, "decision": decision})
            self.telemetry.record(
                event_type="action",
                action=action_data["type"],
                status="ask",
                tokens=action_data.get("tokens", 0),
                cost=action_data.get("cost", 0.0),
                metadata={"decision": decision, "dry_run": dry_run, "args": kwargs},
            )
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

        ok = budget_result["ok"]
        self.telemetry.record(
            event_type="action",
            action=action_data["type"],
            status="allowed" if ok else "budget_blocked",
            tokens=action_data.get("tokens", 0),
            cost=action_data.get("cost", 0.0),
            metadata={"decision": decision, "dry_run": dry_run, "args": kwargs},
        )

        if not ok:
            return {"ok": False, "error": budget_result["reason"], "budget": budget_result}

        return {
            "ok": True,
            "decision": decision,
            "budget": budget_result,
            "action": action_data["type"],
            "args": kwargs,
        }

    def run_workflow(self, workflow_id: str, context: dict[str, Any]) -> dict[str, Any]:
        context = dict(context)
        prompt = context.get("message") or context.get("request") or context.get("query") or workflow_id
        if "persona" not in context and isinstance(prompt, str):
            context["persona"] = self.persona.detect(prompt)["persona"]
        try:
            valid_context = WorkflowContextSchema(**context).model_dump()
        except Exception as e:
            return {"ok": False, "error": f"Invalid workflow context: {e!s}"}
        result = self.workflows.run(workflow_id, valid_context, act=self.act)
        self.telemetry.record(
            event_type="workflow",
            action=workflow_id,
            status="completed" if result.get("ok") else "failed",
            metadata={"context": valid_context, "result": result},
        )
        return result

    def chat_message(self, message: str, session_id: str | None = None) -> dict[str, Any]:
        """Record a chat message and evaluate via policy gates."""
        session = ChatSession(self.project_root, session_id) if session_id else self.chat
        session.add("user", message)
        result = self.act("ChatMessage", content=message, approved=True)
        if result["ok"]:
            reply = f"Acknowledged: {message[:100]}"
            session.add("assistant", reply, metadata={"decision": result["decision"]})
            result["reply"] = reply
        return result

    def run_saga(self, saga_id: str, steps: list[dict[str, Any]], context: dict[str, Any]) -> dict[str, Any]:
        try:
            saga = Saga(
                id=saga_id,
                title=saga_id,
                steps=[SagaStep(**s) for s in steps],
            )
        except Exception as e:
            return {"ok": False, "error": f"Invalid saga definition: {e!s}"}
        result = self.saga.run(saga, context, act=self.act)
        self.telemetry.record(
            event_type="saga",
            action=saga_id,
            status=result.get("status", "unknown"),
            metadata={"context": context, "result": result},
        )
        return result

    def list_workflows(self) -> list[str]:
        return self.workflows.list_workflows()

    def load_plugins(self, memory: MemoryStore | None = None) -> None:
        """Load all enabled plugins and wire memory if available."""
        self.plugins.load_all(memory)

    def save(self) -> None:
        self.budget.save()

    def detect_tech_stack(self) -> dict[str, dict[str, object]]:
        return detect_stack(self.project_root, self.root)

    def spawn_agent(self, agent_id: str, persona: str, scope: list[str], project_root: Path | None = None) -> dict[str, Any]:
        if persona in ("auto", "", "generalist"):
            prompt = " ".join([agent_id, *scope])
            persona = self.persona.detect(prompt)["persona"]
        agent = self.pool.register(agent_id, persona, scope, project_root)
        return {"ok": True, "id": agent.id, "persona": agent.persona, "scope": agent.scope}

    def delegate(self, agent_id: str, action_type: str, **kwargs: Any) -> dict[str, Any]:
        return self.pool.delegate(agent_id, action_type, **kwargs)

    def status(self) -> dict[str, Any]:
        return {
            "version": config.VERSION,
            "root": str(self.root),
            "project_root": str(self.project_root),
            "personas": self.persona.list_personas(),
            "workflows": self.list_workflows(),
            "budgets": list(self.budget.budgets.keys()),
            "rules": [r.name for r in self.policy.rules],
            "plugins": self.plugins.list_plugins(),
            "tech_stack": self.detect_tech_stack(),
            "agents": self.pool.list_agents(),
        }


if __name__ == "__main__":
    k = Kernel()
    print(json.dumps(k.status(), indent=2))
