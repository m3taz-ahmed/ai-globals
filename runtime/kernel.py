#!/usr/bin/env python3
"""AI Global OS runtime kernel."""

from __future__ import annotations

import copy
import functools
import json
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

import config

from .approval_cache import ApprovalCache
from .audit import AuditLogger
from .budget import BudgetManager
from .chat import ChatSession
from .governance import GovernanceHooks
from .guardian import ActionRequest, DecisionStatus, Guardian
from .metrics import CollectorRegistry, Counter, Gauge
from .orchestrator import AgentPool
from .persona import PersonaDetector
from .plugin import PluginManager
from .policy import PolicyEngine
from .preloop import FeedbackLoop, Outcome
from .probity import Guardrails
from .saga import Saga, SagaOrchestrator, SagaStep
from .skill_resolver import SkillResolver
from .sovereign import AgentCapabilities
from .tech_stack import detect_stack
from .telemetry import TelemetryCollector
from .tracing import ConsoleSpanExporter, TracerProvider, with_span
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


# Context keys that are auto-derived and should be recomputed for a fresh context.
_FRESH_CONTEXT_DERIVED_KEYS = {"persona", "personas", "skill", "skills", "lords"}


class Kernel:
    """Central runtime for AI Global OS."""

    def __init__(
        self,
        root: Path | None = None,
        project_root: Path | None = None,
        persona_detector: PersonaDetector | None = None,
        skill_resolver: SkillResolver | None = None,
    ) -> None:
        self.root = root or config.discover_root()
        self.project_root = project_root or root or config.discover_project_root()
        self.skill_resolver = skill_resolver or SkillResolver(self.root, self.project_root)
        self.persona = persona_detector or PersonaDetector(skill_resolver=self.skill_resolver)
        self.policy = PolicyEngine(self.root, self.project_root)
        self.budget = BudgetManager(self.project_root)
        self.workflows = WorkflowRunner(self.project_root, self.root, persona_detector=self.persona)
        self.saga = self._build_saga_orchestrator()
        self.telemetry = self._build_telemetry_collector()
        self.chat = ChatSession(self.project_root)
        self.pool = AgentPool(self.root)
        self.audit = AuditLogger(self.project_root)
        self.approval_cache = ApprovalCache()
        self.guardian = self._build_guardian()
        self.probity = self._build_probity()
        self.capabilities = AgentCapabilities()
        self.metrics = self._build_metrics()
        self.tracer = self._build_tracer()
        self.preloop = FeedbackLoop()
        self.governance = GovernanceHooks(self.audit, self.telemetry)
        self.plugins = PluginManager(self, self.root)

    def _build_saga_orchestrator(self) -> SagaOrchestrator:
        return SagaOrchestrator(self.project_root)

    def _build_telemetry_collector(self) -> TelemetryCollector:
        return TelemetryCollector(self.project_root)

    def _build_guardian(self) -> Guardian:
        path = self.project_root / "runtime" / "policies" / "guardian.yaml"
        if path.exists():
            return Guardian.from_yaml(path)
        return Guardian([])

    def _build_probity(self) -> Guardrails:
        path = self.project_root / "runtime" / "policies" / "probity.yaml"
        if path.exists():
            import yaml

            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            return Guardrails(data)
        return Guardrails()

    def _build_metrics(self) -> CollectorRegistry:
        registry = CollectorRegistry()
        self._actions_total: Counter = Counter("aios_actions_total", "Total actions evaluated", ("action", "decision"))
        self._workflows_total: Counter = Counter("aios_workflows_total", "Total workflows executed", ("status",))
        self._sagas_total: Counter = Counter("aios_sagas_total", "Total sagas executed", ("status",))
        self._guardian_denials_total: Counter = Counter("aios_guardian_denials", "Total guardian denials", ("rule",))
        self._probity_violations_total: Counter = Counter("aios_probity_violations", "Total probity violations", ("rule",))
        self._budget_gauge: Gauge = Gauge("aios_budget_remaining", "Remaining budget for active scopes", ("scope",))
        registry.register(self._actions_total)
        registry.register(self._workflows_total)
        registry.register(self._sagas_total)
        registry.register(self._guardian_denials_total)
        registry.register(self._probity_violations_total)
        registry.register(self._budget_gauge)
        return registry

    def _build_tracer(self) -> TracerProvider:
        provider = TracerProvider()
        provider.add_span_processor(ConsoleSpanExporter(self.project_root / "state" / "spans.jsonl"))
        return provider

    def detect_persona(self, text: str) -> dict[str, Any]:
        """Detect the best persona for a user prompt."""
        return self.persona.detect(text)

    def _auto_persona(self, kwargs: dict[str, Any]) -> None:
        """Inject personas and skills into kwargs if missing and text is present."""
        if "personas" in kwargs or "persona" in kwargs:
            return
        text = kwargs.get("message") or kwargs.get("content") or kwargs.get("query") or kwargs.get("request")
        if isinstance(text, str) and text.strip():
            result = self.persona.detect_multiple(text)
            kwargs["persona"] = result["persona"]
            kwargs["skill"] = result["skill"]
            kwargs["personas"] = result["personas"]
            kwargs["skills"] = result["skills"]
            kwargs["lords"] = result["lords"]

    def _check_cached_approval(self, action_data: dict[str, Any]) -> bool:
        return self.approval_cache.is_approved(action_data)

    def _cache_approval(self, action_data: dict[str, Any], dry_run: bool) -> None:
        if not dry_run:
            self.approval_cache.approve(action_data)

    def _handle_policy_denied(
        self,
        action_data: dict[str, Any],
        kwargs: dict[str, Any],
        decision: dict[str, Any],
        dry_run: bool,
    ) -> dict[str, Any]:
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

    def _handle_policy_ask(
        self,
        action_data: dict[str, Any],
        kwargs: dict[str, Any],
        decision: dict[str, Any],
        dry_run: bool,
    ) -> dict[str, Any]:
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

    def _resolve_approval(self, action_data: dict[str, Any], dry_run: bool) -> bool:
        if action_data.get("approved"):
            self._cache_approval(action_data, dry_run)
            return True
        if self._check_cached_approval(action_data):
            action_data["approved"] = True
            return True
        return False

    def _build_budget_kwargs(
        self, action_data: dict[str, Any], session_id: str | None = None
    ) -> dict[str, Any]:
        budget_kwargs: dict[str, Any] = {}
        if "rollout_id" in action_data:
            budget_kwargs["rollout_id"] = action_data["rollout_id"]
        if "token_weight" in action_data:
            budget_kwargs["token_weight"] = action_data["token_weight"]
        if "input_tokens" in action_data and "output_tokens" in action_data:
            budget_kwargs["input_tokens"] = action_data["input_tokens"]
            budget_kwargs["output_tokens"] = action_data["output_tokens"]
        if session_id is not None:
            budget_kwargs["session_id"] = session_id
        return budget_kwargs

    def _audit_budget(
        self,
        action_data: dict[str, Any],
        kwargs: dict[str, Any],
        decision: dict[str, Any],
        budget_result: dict[str, Any],
        dry_run: bool,
    ) -> None:
        if dry_run:
            return
        self.budget.save()
        if not budget_result["ok"]:
            self.audit.log("budget.blocked", {"action": action_data["type"], "args": kwargs, "budget": budget_result})
        else:
            self.audit.log("action.allowed", {"action": action_data["type"], "args": kwargs, "decision": decision, "budget": budget_result})

    def _finalize_action(
        self,
        action_data: dict[str, Any],
        kwargs: dict[str, Any],
        decision: dict[str, Any],
        budget_result: dict[str, Any],
        dry_run: bool,
    ) -> dict[str, Any]:
        self._audit_budget(action_data, kwargs, decision, budget_result, dry_run)
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

    def _check_guardian(self, action_type: str, action_data: dict[str, Any]) -> dict[str, Any] | None:
        """Run guardian-angel policy and return an error response if denied."""
        try:
            decision = self.guardian.authorize(
                ActionRequest(tool=action_type, attributes={"action": action_data, "args": action_data})
            )
        except Exception:
            return None
        if decision.status == DecisionStatus.DENY:
            self._guardian_denials_total.labels(rule=decision.rule_name).inc()
            return {
                "ok": False,
                "error": f"Guardian denied by {decision.rule_name}",
                "decision": {"rule": decision.rule_name, "reason": decision.reason},
            }
        if decision.status == DecisionStatus.REQUIRE_APPROVAL:
            return {
                "ok": False,
                "error": f"Guardian requires approval for {decision.rule_name}",
                "requires_approval": True,
                "decision": {"rule": decision.rule_name, "reason": decision.reason},
            }
        return None

    def _check_probity(self, action_type: str, action_data: dict[str, Any]) -> None:
        """Run probity guardrails for write and command actions."""
        event: dict[str, Any] = {"type": action_type, "history": []}
        if action_type in ("write", "edit"):
            event["path"] = str(action_data.get("path", ""))
            event["content"] = str(action_data.get("content", ""))
        elif action_type in ("exec", "command", "shell"):
            event["command"] = str(action_data.get("command", ""))
        try:
            self.probity.check(event)
        except Exception as exc:
            rule = getattr(exc, "rule_name", "unknown")
            self._probity_violations_total.labels(rule=rule).inc()
            raise

    def act(self, action_type: str, dry_run: bool = False, **kwargs: Any) -> dict[str, Any]:
        """Evaluate action through policy + budget + governance gates."""
        fresh_context = kwargs.pop("fresh_context", False)
        session_id = kwargs.pop("session_id", None)
        with with_span(self.tracer.get_tracer("kernel"), f"act.{action_type}"):
            self._auto_persona(kwargs)
            if fresh_context and session_id is None:
                session_id = uuid.uuid4().hex
            try:
                action_data = ActionSchema(type=action_type, **kwargs).model_dump()
            except ValidationError as e:
                return {"ok": False, "error": f"Invalid action arguments: {e!s}"}

            self._check_probity(action_type, action_data)

            guard = self._check_guardian(action_type, action_data)
            if guard:
                return guard

            decision = self.policy.can(action_data["type"], **action_data)
            if decision["decision"] == "deny":
                self._actions_total.labels(action=action_type, decision="deny").inc()
                return self._handle_policy_denied(action_data, kwargs, decision, dry_run)

            if decision["decision"] == "ask" and not self._resolve_approval(action_data, dry_run):
                self._actions_total.labels(action=action_type, decision="ask").inc()
                return self._handle_policy_ask(action_data, kwargs, decision, dry_run)

            self._actions_total.labels(action=action_type, decision="allow").inc()

            budget_result = self.budget.check(
                "session",
                action_data.get("tokens", 0),
                action_data.get("cost", 0.0),
                dry_run=dry_run,
                **self._build_budget_kwargs(action_data, session_id=session_id),
            )
            result = self._finalize_action(action_data, kwargs, decision, budget_result, dry_run)
            self.preloop.record(
                Outcome(
                    action=action_type,
                    ok=result.get("ok", False),
                    reward=1.0 if result.get("ok") else 0.0,
                    tags=[decision["decision"]],
                )
            )
            return result

    def run_workflow(
        self, workflow_id: str, context: dict[str, Any], fresh_context: bool = False
    ) -> dict[str, Any]:
        if fresh_context:
            context = copy.deepcopy(context)
            for key in _FRESH_CONTEXT_DERIVED_KEYS:
                context.pop(key, None)
        else:
            context = dict(context)
        session_id: str | None = None
        if fresh_context:
            session_id = uuid.uuid4().hex
        prompt = context.get("message") or context.get("request") or context.get("query") or workflow_id
        if "personas" not in context and "persona" not in context and isinstance(prompt, str):
            result = self.persona.detect_multiple(prompt)
            context["persona"] = result["persona"]
            context["skill"] = result["skill"]
            context["personas"] = result["personas"]
            context["skills"] = result["skills"]
            context["lords"] = result["lords"]
        try:
            valid_context = WorkflowContextSchema(**context).model_dump()
        except ValidationError as e:
            return {"ok": False, "error": f"Invalid workflow context: {e!s}"}
        act = self.act
        if session_id is not None:
            act = functools.partial(self.act, session_id=session_id)
        result = self.workflows.run(workflow_id, valid_context, act=act)
        if session_id is not None:
            result["session_id"] = session_id
        self.telemetry.record(
            event_type="workflow",
            action=workflow_id,
            status="completed" if result.get("ok") else "failed",
            metadata={"context": valid_context, "result": result},
        )
        return result

    def chat_message(
        self, message: str, session_id: str | None = None, fresh_context: bool = False
    ) -> dict[str, Any]:
        """Record a chat message and evaluate via policy gates."""
        if fresh_context:
            session_id = session_id or uuid.uuid4().hex
            session = ChatSession(self.project_root, session_id)
        else:
            session = ChatSession(self.project_root, session_id) if session_id else self.chat
        session.add("user", message)
        result = self.act("ChatMessage", content=message, approved=True, session_id=session_id, fresh_context=fresh_context)
        if result["ok"]:
            reply = f"Acknowledged: {message[:100]}"
            session.add("assistant", reply, metadata={"decision": result["decision"]})
            result["reply"] = reply
        if session_id is not None:
            result["session_id"] = session_id
        return result

    def run_saga(
        self,
        saga_id: str,
        steps: list[dict[str, Any]],
        context: dict[str, Any],
        fresh_context: bool = False,
    ) -> dict[str, Any]:
        if fresh_context:
            context = copy.deepcopy(context)
            for key in _FRESH_CONTEXT_DERIVED_KEYS:
                context.pop(key, None)
        else:
            context = dict(context)
        try:
            saga = Saga(
                id=saga_id,
                title=saga_id,
                steps=[SagaStep(**s) for s in steps],
            )
        except ValidationError as e:
            return {"ok": False, "error": f"Invalid saga definition: {e!s}"}
        session_id: str | None = None
        if fresh_context:
            session_id = uuid.uuid4().hex
        act = self.act
        if session_id is not None:
            act = functools.partial(self.act, session_id=session_id)
        result = self.saga.run(saga, context, act=act)
        if session_id is not None:
            result["session_id"] = session_id
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

    def spawn_agent(
        self,
        agent_id: str,
        persona: str,
        scope: list[str],
        project_root: Path | None = None,
        lords: list[str] | None = None,
    ) -> dict[str, Any]:
        extra_lords: list[str] = list(lords or [])
        if persona in ("auto", "", "generalist"):
            prompt = " ".join([agent_id, *scope])
            result = self.persona.detect_multiple(prompt)
            personas = result["personas"]
            extra_lords = sorted(set(extra_lords + result["lords"]))
        else:
            personas = [p.strip() for p in persona.split(",") if p.strip()]
            if not personas:
                return {"ok": False, "error": "No persona provided"}
        agent = self.pool.register(agent_id, personas, scope, project_root, lords=extra_lords)
        return {
            "ok": True,
            "id": agent.id,
            "persona": agent.persona,
            "personas": agent.personas,
            "lords": agent.lords,
            "scope": agent.scope,
        }

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
            "skills": self.skill_resolver.list_skills(),
            "plugins": self.plugins.list_plugins(),
            "tech_stack": self.detect_tech_stack(),
            "agents": self.pool.list_agents(),
            "metrics": self.metrics.names(),
            "guardian_rules": [r.get("name", "unnamed") for r in self.guardian.rules],
            "capabilities": self.capabilities.list(),
        }


if __name__ == "__main__":
    k = Kernel()
    print(json.dumps(k.status(), indent=2))
