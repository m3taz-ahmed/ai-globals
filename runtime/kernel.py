#!/usr/bin/env python3
"""aiZee runtime kernel — facade delegating to manager submodules."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

import config

from .approval_cache import ApprovalCache
from .audit import AuditLogger
from .budget import BudgetManager
from .enums import Decision
from .governance import GovernanceHooks
from .managers import AgentManager, ChatManager, PolicyManager, WorkflowManager
from .metrics import CollectorRegistry, Counter, Gauge
from .persona import PersonaDetector
from .preloop import FeedbackLoop
from .skill_resolver import SkillResolver
from .sovereign import AgentCapabilities
from .tech_stack import detect_stack
from .telemetry import TelemetryCollector
from .tracing import ConsoleSpanExporter, TracerProvider, with_span

if TYPE_CHECKING:
    from memory.store import MemoryStore

    from .plugin import PluginManager


class ActionSchema(BaseModel):
    """Validated action envelope for Kernel.act().

    The `type`, `tokens`, and `cost` fields are strictly typed. Extra fields
    are intentionally allowed because action parameters are dynamic — e.g.
    `command` for bash, `file_path` for write, `content` for edit. These
    extra fields are forwarded to the policy engine's YAML rule conditions
    via ``**action_data``. Forbidding extras would require a schema per
    action type, which is incompatible with user-defined YAML policies.
    """

    model_config = ConfigDict(extra="allow")

    type: str = Field(..., min_length=1)
    tokens: int = Field(default=0, ge=0)
    cost: float = Field(default=0.0, ge=0.0)


class Kernel:
    """Central runtime for aiZee.

    Acts as a facade delegating to PolicyManager, WorkflowManager,
    AgentManager, and ChatManager. Each manager owns a single
    responsibility cluster.
    """

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

        # Core services
        self.budget = BudgetManager(self.project_root)
        self.telemetry = self._build_telemetry_collector()
        self.audit = AuditLogger(self.project_root)
        self.approval_cache = ApprovalCache()
        self.preloop = FeedbackLoop()
        self.capabilities = AgentCapabilities()
        self.metrics = self._build_metrics()
        self.tracer = self._build_tracer()
        self.governance = GovernanceHooks(self.audit, self.telemetry)

        # Managers
        self.policy_mgr = PolicyManager(
            self.root, self.project_root, self.audit, self.budget,
            self.approval_cache, self.preloop,
            self._actions_total, self._guardian_denials_total, self._probity_violations_total,
        )
        self.workflow_mgr = WorkflowManager(
            self.project_root, self.root, self.persona, self._sagas_total,
        )
        self.agent_mgr = AgentManager(self.root, self.persona)
        self.chat_mgr = ChatManager(self.project_root)

        # Backward-compatible direct attributes (settable for tests)
        self.policy = self.policy_mgr.policy
        self.guardian = self.policy_mgr.guardian
        self.probity = self.policy_mgr.probity
        self.workflows = self.workflow_mgr.workflows
        self.saga = self.workflow_mgr.saga
        self.pool = self.agent_mgr.pool
        self.chat = self.chat_mgr.default_session

        # Plugin manager — lazily initialized to avoid loading plugins on kernel creation
        self._plugins: PluginManager | None = None

    @property
    def plugins(self) -> PluginManager:
        """Lazily initialize the PluginManager on first access."""
        if self._plugins is None:
            from .plugin import PluginManager

            self._plugins = PluginManager(self, self.root)
        return self._plugins

    # --- Builders ---
    def _build_telemetry_collector(self) -> TelemetryCollector:
        return TelemetryCollector(self.project_root)

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

    # --- Persona ---
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

    # --- Action evaluation (delegates to PolicyManager) ---
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

            self.policy_mgr.check_probity(action_type, action_data, self.probity)

            guard = self.policy_mgr.check_guardian(action_type, action_data, self.guardian)
            if guard:
                return guard

            decision = self.policy.can(action_data["type"], **action_data)
            if decision["decision"] == Decision.DENY.value:
                self._actions_total.labels(action=action_type, decision=Decision.DENY.value).inc()
                return self.policy_mgr.handle_policy_denied(action_data, kwargs, decision, dry_run, self.telemetry)

            if decision["decision"] == Decision.ASK.value and not self.policy_mgr.resolve_approval(action_data, dry_run):
                self._actions_total.labels(action=action_type, decision=Decision.ASK.value).inc()
                return self.policy_mgr.handle_policy_ask(action_data, kwargs, decision, dry_run, self.telemetry)

            self._actions_total.labels(action=action_type, decision=Decision.ALLOW.value).inc()

            budget_result = self.budget.check(
                "session",
                action_data.get("tokens", 0),
                action_data.get("cost", 0.0),
                dry_run=dry_run,
                **self.policy_mgr.build_budget_kwargs(action_data, session_id=session_id),
            )
            result = self.policy_mgr.finalize_action(action_data, kwargs, decision, budget_result, dry_run, self.telemetry)
            self.policy_mgr.record_preloop(action_type, result, decision)
            return result

    # --- Workflow (delegates to WorkflowManager) ---
    def run_workflow(
        self, workflow_id: str, context: dict[str, Any], fresh_context: bool = False
    ) -> dict[str, Any]:
        return self.workflow_mgr.run_workflow(
            workflow_id, context, self.act, fresh_context, self.persona, self.telemetry
        )

    # --- Chat (delegates to ChatManager) ---
    def chat_message(
        self, message: str, session_id: str | None = None, fresh_context: bool = False
    ) -> dict[str, Any]:
        return self.chat_mgr.chat_message(message, session_id, fresh_context, self.act)

    # --- Saga (delegates to WorkflowManager) ---
    def run_saga(
        self,
        saga_id: str,
        steps: list[dict[str, Any]],
        context: dict[str, Any],
        fresh_context: bool = False,
    ) -> dict[str, Any]:
        return self.workflow_mgr.run_saga(saga_id, steps, context, self.act, fresh_context, self.telemetry)

    # --- Agent (delegates to AgentManager) ---
    def spawn_agent(
        self,
        agent_id: str,
        persona: str,
        scope: list[str],
        project_root: Path | None = None,
        lords: list[str] | None = None,
    ) -> dict[str, Any]:
        return self.agent_mgr.spawn_agent(agent_id, persona, scope, project_root, lords)

    def delegate(self, agent_id: str, action_type: str, **kwargs: Any) -> dict[str, Any]:
        return self.agent_mgr.delegate(agent_id, action_type, **kwargs)

    # --- Misc ---
    def list_workflows(self) -> list[str]:
        return self.workflow_mgr.list_workflows()

    def load_plugins(self, memory: MemoryStore | None = None) -> None:
        """Load all enabled plugins and wire memory if available."""
        self.plugins.load_all(memory)

    def save(self) -> None:
        self.budget.save()

    def detect_tech_stack(self) -> dict[str, dict[str, object]]:
        """Detect tech stack, cached per kernel instance."""
        if not hasattr(self, "_tech_stack_cache"):
            self._tech_stack_cache: dict[str, dict[str, object]] = detect_stack(self.project_root, self.root)
        return self._tech_stack_cache

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
            "agents": self.agent_mgr.list_agents(),
            "metrics": self.metrics.names(),
            "guardian_rules": [r.get("name", "unnamed") for r in self.guardian.rules],
            "capabilities": self.capabilities.list(),
        }


if __name__ == "__main__":
    k = Kernel()
    print(json.dumps(k.status(), indent=2))
