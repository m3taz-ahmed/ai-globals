#!/usr/bin/env python3
"""aiZee runtime kernel — facade delegating to manager submodules."""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

import config

from .approval_cache import ApprovalCache
from .audit import AuditLogger
from .budget import BudgetManager
from .enums import Decision
from .governance import GovernanceHooks
from .loop_detector import LoopDetector
from .managers import AgentManager, ChatManager, PolicyManager, WorkflowManager
from .mcp_firewall import McpFirewall
from .metrics import CollectorRegistry, Counter, Gauge
from .middleware import (
    ActionContext,
    CompiledPipeline,
    Middleware,
    MiddlewarePipeline,
    MiddlewareResult,
)
from .persona import PersonaDetector, inject_persona_context
from .preloop import FeedbackLoop
from .probity import GuardrailViolationError
from .skill_resolver import SkillResolver
from .sovereign import AgentCapabilities
from .tech_stack import detect_stack
from .telemetry import TelemetryCollector
from .tracing import ConsoleSpanExporter, TracerProvider, with_span

if TYPE_CHECKING:
    from memory.store import MemoryStore

    from .chat import ChatSession
    from .guardian import Guardian
    from .orchestrator import AgentPool
    from .plugin import PluginManager
    from .policy import PolicyEngine
    from .probity import Guardrails
    from .saga import SagaOrchestrator
    from .workflow import WorkflowRunner


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


# --- Module-level kernel helpers ---


def _init_core_services(kernel: Kernel) -> None:
    """Initialize core runtime services (budget, telemetry, audit, etc.)."""
    kernel.budget = BudgetManager(kernel.project_root)
    kernel.telemetry = kernel._build_telemetry_collector()
    kernel.audit = AuditLogger(kernel.project_root)
    kernel.approval_cache = ApprovalCache()
    kernel.preloop = FeedbackLoop()
    kernel.capabilities = AgentCapabilities()
    kernel.metrics = kernel._build_metrics()
    kernel.tracer = kernel._build_tracer()
    kernel.governance = GovernanceHooks(kernel.audit, kernel.telemetry)
    kernel.mcp_firewall = kernel._build_mcp_firewall()
    kernel.loop_detector = LoopDetector(window=20, threshold=5)


def _init_managers(kernel: Kernel) -> None:
    """Initialize manager submodules (policy, workflow, agent, chat)."""
    kernel.policy_mgr = PolicyManager(
        kernel.root, kernel.project_root, kernel.audit, kernel.budget,
        kernel.approval_cache, kernel.preloop,
        kernel._actions_total, kernel._guardian_denials_total, kernel._probity_violations_total,
    )
    kernel.workflow_mgr = WorkflowManager(
        kernel.project_root, kernel.root, kernel.persona, kernel._sagas_total,
    )
    kernel.agent_mgr = AgentManager(kernel.root, kernel.persona)
    # LocalResponder reads live kernel state lazily via the bound method.
    from runtime.local_responder import LocalResponder

    kernel.chat_mgr = ChatManager(
        kernel.project_root, responder=LocalResponder(context_provider=kernel.status),
    )


def _init_compat_attributes(kernel: Kernel) -> None:
    """Set backward-compatible direct attributes (settable for tests)."""
    kernel.policy = kernel.policy_mgr.policy
    kernel.guardian = kernel.policy_mgr.guardian
    kernel.probity = kernel.policy_mgr.probity
    kernel.workflows = kernel.workflow_mgr.workflows
    kernel.saga = kernel.workflow_mgr.saga
    kernel.pool = kernel.agent_mgr.pool
    kernel.chat = kernel.chat_mgr.default_session


def _auto_persona(kernel: Kernel, kwargs: dict[str, Any]) -> None:
    """Inject personas and skills into kwargs if missing and text is present."""
    inject_persona_context(
        kernel.persona, kwargs, text_keys=("message", "content", "query", "request"),
    )


def _run_probity_gate(
    kernel: Kernel, action_type: str, action_data: dict[str, Any],
) -> dict[str, Any] | None:
    """Check probity gate; return denial dict on violation, None on pass."""
    try:
        kernel.policy_mgr.check_probity(action_type, action_data, kernel.probity)
    except GuardrailViolationError as exc:
        kernel._probity_violations_total.labels(rule=exc.rule_name).inc()
        kernel.audit.log("probity.deny", {"action": action_type, "rule": exc.rule_name, "detail": str(exc)})
        kernel._actions_total.labels(action=action_type, decision=Decision.DENY.value).inc()
        return {
            "ok": False,
            "decision": Decision.DENY.value,
            "reason": f"probity_violation: {exc.rule_name}",
            "gate": "probity",
            "detail": str(exc),
        }
    return None


def _run_guardian_gate(
    kernel: Kernel, action_type: str, action_data: dict[str, Any],
) -> dict[str, Any] | None:
    """Check guardian gate; return denial dict on guard, None on pass."""
    guard = kernel.policy_mgr.check_guardian(action_type, action_data, kernel.guardian)
    if guard:
        return guard
    return None


def _run_policy_gate(
    kernel: Kernel,
    action_type: str,
    action_data: dict[str, Any],
    kwargs: dict[str, Any],
    decision: dict[str, Any],
    dry_run: bool,
) -> dict[str, Any] | None:
    """Check policy gate; return denial/ask dict or None to continue."""
    if decision["decision"] == Decision.DENY.value:
        kernel._actions_total.labels(action=action_type, decision=Decision.DENY.value).inc()
        return kernel.policy_mgr.handle_policy_denied(action_data, kwargs, decision, dry_run, kernel.telemetry)
    if decision["decision"] == Decision.ASK.value and not kernel.policy_mgr.resolve_approval(action_data, dry_run):
        kernel._actions_total.labels(action=action_type, decision=Decision.ASK.value).inc()
        return kernel.policy_mgr.handle_policy_ask(action_data, kwargs, decision, dry_run, kernel.telemetry)
    return None


def _run_loop_detection(
    kernel: Kernel, action_type: str, action_data: dict[str, Any], dry_run: bool,
) -> dict[str, Any] | None:
    """Check loop detection; return denial dict on loop hit, None otherwise."""
    skip_loop = dry_run or kernel.policy_mgr.approval_cache.is_approved(action_data)
    loop_hit = None if skip_loop else kernel.loop_detector.check_and_record(action_type, action_data)
    if loop_hit is not None:
        kernel._actions_total.labels(action=action_type, decision=Decision.DENY.value).inc()
        return {
            "ok": False,
            "decision": Decision.DENY.value,
            "reason": f"loop detected: {loop_hit.tool} repeated {loop_hit.repeat_count}x in window {loop_hit.window}",
            "loop": True,
            "repeat_count": loop_hit.repeat_count,
        }
    return None


def _finalize_action(
    kernel: Kernel,
    action_type: str,
    action_data: dict[str, Any],
    kwargs: dict[str, Any],
    decision: dict[str, Any],
    dry_run: bool,
    session_id: str | None,
) -> dict[str, Any]:
    """Run budget check and finalize the action."""
    budget_result = kernel.budget.check(
        "session",
        action_data.get("tokens", 0),
        action_data.get("cost", 0.0),
        dry_run=dry_run,
        **kernel.policy_mgr.build_budget_kwargs(action_data, session_id=session_id),
    )
    result = kernel.policy_mgr.finalize_action(action_data, kwargs, decision, budget_result, dry_run, kernel.telemetry)
    kernel.policy_mgr.record_preloop(action_type, result, decision)
    return result


def _act_via_middleware(
    kernel: Kernel,
    action_type: str,
    dry_run: bool,
    kwargs: dict[str, Any],
    session_id: str | None,
) -> dict[str, Any]:
    """Execute action through the flat middleware array (Pattern 4).

    The direct path is wrapped as the terminal handler. Middlewares can
    observe, transform, or short-circuit before reaching the handler.
    """
    context = ActionContext(
        action_type=action_type,
        data=dict(kwargs),
        dry_run=dry_run,
        session_id=session_id,
    )

    def handler(ctx: ActionContext) -> MiddlewareResult[dict[str, Any]]:
        result = kernel._act_direct(
            ctx.action_type, ctx.dry_run, ctx.data, ctx.session_id, fresh_context=False,
        )
        return MiddlewareResult(ok=bool(result.get("ok", False)), data=result)

    mw_result = kernel._middleware_pipeline.execute(context, handler)
    if mw_result.ok:
        return mw_result.data if mw_result.data is not None else {"ok": True}
    err_msg = str(mw_result.error) if mw_result.error else "middleware error"
    return {"ok": False, "error": err_msg}


def _act_via_compiled_pipeline(
    kernel: Kernel,
    action_type: str,
    dry_run: bool,
    kwargs: dict[str, Any],
    session_id: str | None,
    pipeline: CompiledPipeline,
) -> dict[str, Any]:
    """Execute action through the pre-compiled enhancer pipeline (Pattern 5)."""
    context = ActionContext(
        action_type=action_type,
        data=dict(kwargs),
        dry_run=dry_run,
        session_id=session_id,
    )
    result = pipeline.execute(context)
    if result.ok:
        return result.data if result.data is not None else {"ok": True}
    err_msg = str(result.error) if result.error else "pipeline error"
    return {"ok": False, "error": err_msg}


def _get_compiled_pipeline(kernel: Kernel, action_type: str) -> CompiledPipeline | None:
    """Get or lazily compile the pipeline for an action type.

    Returns None if no builder is registered for the action type.
    On first access, the builder configures the pipeline and it is
    compiled and cached. Subsequent calls return the cached instance.
    """
    if action_type not in kernel._pipeline_builders:
        return None
    if action_type not in kernel._compiled_pipelines:
        pipeline = CompiledPipeline()
        kernel._pipeline_builders[action_type](pipeline)
        pipeline.compile()
        kernel._compiled_pipelines[action_type] = pipeline
    return kernel._compiled_pipelines[action_type]


class Kernel:
    """Central runtime for aiZee.

    Acts as a facade delegating to PolicyManager, WorkflowManager,
    AgentManager, and ChatManager. Each manager owns a single
    responsibility cluster.
    """

    budget: BudgetManager
    telemetry: TelemetryCollector
    audit: AuditLogger
    approval_cache: ApprovalCache
    preloop: FeedbackLoop
    capabilities: AgentCapabilities
    metrics: CollectorRegistry
    tracer: TracerProvider
    governance: GovernanceHooks
    mcp_firewall: McpFirewall
    loop_detector: LoopDetector
    policy_mgr: PolicyManager
    workflow_mgr: WorkflowManager
    agent_mgr: AgentManager
    chat_mgr: ChatManager
    policy: PolicyEngine
    guardian: Guardian
    probity: Guardrails
    workflows: WorkflowRunner
    saga: SagaOrchestrator
    pool: AgentPool
    chat: ChatSession

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
        _init_core_services(self)
        _init_managers(self)
        _init_compat_attributes(self)
        # Plugin manager — lazily initialized to avoid loading plugins on kernel creation
        self._plugins: PluginManager | None = None
        # Pattern 4: Flat middleware array (tRPC-style callRecursive)
        self._middleware_pipeline = MiddlewarePipeline()
        # Pattern 5: Pre-compiled enhancer pipeline (NestJS-style)
        # Builders configure a CompiledPipeline per action type; compiled
        # pipelines are cached after first execution.
        self._pipeline_builders: dict[str, Callable[[CompiledPipeline], None]] = {}
        self._compiled_pipelines: dict[str, CompiledPipeline] = {}

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
        self._actions_total: Counter = Counter("aizee_actions_total", "Total actions evaluated", ("action", "decision"))
        self._workflows_total: Counter = Counter("aizee_workflows_total", "Total workflows executed", ("status",))
        self._sagas_total: Counter = Counter("aizee_sagas_total", "Total sagas executed", ("status",))
        self._guardian_denials_total: Counter = Counter("aizee_guardian_denials", "Total guardian denials", ("rule",))
        self._probity_violations_total: Counter = Counter("aizee_probity_violations", "Total probity violations", ("rule",))
        self._budget_gauge: Gauge = Gauge("aizee_budget_remaining", "Remaining budget for active scopes", ("scope",))
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

    def _build_mcp_firewall(self) -> McpFirewall:
        """Load MCP firewall rules from OS + project policy files."""
        from runtime.mcp_firewall import McpFirewall

        os_rules = self.root / "runtime" / "policies" / "mcp_firewall.yaml"
        fw = McpFirewall.from_yaml(os_rules)
        project_rules = self.project_root / ".aizee" / "mcp_firewall.yaml"
        if project_rules.exists():
            for rule in McpFirewall.from_yaml(project_rules).rules:
                fw.add_rule(rule)
        return fw

    def detect_persona(self, text: str) -> dict[str, Any]:
        """Detect the best persona for a user prompt."""
        return self.persona.detect(text)

    # --- Action evaluation (delegates to PolicyManager) ---
    def act(self, action_type: str, dry_run: bool = False, **kwargs: Any) -> dict[str, Any]:
        """Evaluate action through policy + budget + governance gates.

        Dispatches to middleware pipeline (if registered) or direct gated path.
        """
        fresh_context = kwargs.pop("fresh_context", False)
        session_id = kwargs.pop("session_id", None)
        with with_span(self.tracer.get_tracer("kernel"), f"act.{action_type}"):
            _auto_persona(self, kwargs)
            if fresh_context and session_id is None:
                session_id = uuid.uuid4().hex
            if self._middleware_pipeline.has_middlewares():
                return _act_via_middleware(self, action_type, dry_run, kwargs, session_id)
            return self._act_direct(action_type, dry_run, kwargs, session_id, fresh_context)

    def _act_direct(
        self,
        action_type: str,
        dry_run: bool,
        kwargs: dict[str, Any],
        session_id: str | None,
        fresh_context: bool,
    ) -> dict[str, Any]:
        """Existing direct action evaluation path (guardian → policy → budget)."""
        try:
            action_data = ActionSchema(type=action_type, **kwargs).model_dump()
        except ValidationError as e:
            return {"ok": False, "error": f"Invalid action arguments: {e!s}"}
        probity_result = _run_probity_gate(self, action_type, action_data)
        if probity_result is not None:
            return probity_result
        if fresh_context:
            self.loop_detector.reset()
        guardian_result = _run_guardian_gate(self, action_type, action_data)
        if guardian_result is not None:
            return guardian_result
        decision = self.policy.can(action_data["type"], **action_data)
        policy_result = _run_policy_gate(self, action_type, action_data, kwargs, decision, dry_run)
        if policy_result is not None:
            return policy_result
        loop_result = _run_loop_detection(self, action_type, action_data, dry_run)
        if loop_result is not None:
            return loop_result
        self._actions_total.labels(action=action_type, decision=Decision.ALLOW.value).inc()
        return _finalize_action(self, action_type, action_data, kwargs, decision, dry_run, session_id)

    # --- Middleware & Pipeline Registration ---

    def use_middleware(self, mw: Middleware) -> None:
        """Register a global middleware (Pattern 4 — tRPC-style).

        Once at least one middleware is registered, ``act()`` dispatches
        through the flat middleware array instead of the direct path.
        """
        self._middleware_pipeline.use(mw)

    def register_action_pipeline(
        self,
        action_type: str,
        builder: Callable[[CompiledPipeline], None],
    ) -> None:
        """Register a compiled pipeline builder for an action type (Pattern 5).

        .. deprecated::
            GATE-B4: This API allowed gate-free handlers that could bypass
            the 5-gate pipeline. It is no longer dispatched from ``act()``.
            All actions now flow through the gated ``_act_direct`` path.
            Will be removed in the next minor version.

        The builder receives a ``CompiledPipeline`` and adds guards,
        interceptors, pipes, and a handler. The pipeline is compiled on
        first ``act()`` call for that action type and cached thereafter.
        """
        import warnings

        warnings.warn(
            "register_action_pipeline() is deprecated (GATE-B4) and no longer "
            "dispatched from act(). All actions flow through the gated path. "
            "Will be removed in the next minor version.",
            DeprecationWarning,
            stacklevel=2,
        )
        self._pipeline_builders[action_type] = builder
        # Invalidate any previously cached compiled pipeline for this action
        self._compiled_pipelines.pop(action_type, None)

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

    def check_mcp_tool(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Evaluate an MCP tool call through the firewall.

        Returns a decision dict (``decision``/``rule``/``reason``/``tool``)
        compatible with the policy pipeline. Callers should block on
        ``decision == "deny"`` and request approval on ``"ask"``.
        """
        return self.mcp_firewall.check(tool_name, args)

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
            "mcp_firewall_rules": len(self.mcp_firewall.rules),
            "loop_detector": self.loop_detector.stats(),
        }


class KernelBuilder:
    """Builder for Kernel with custom dependency injection.

    Usage:
        kernel = (KernelBuilder()
            .with_root(Path("/custom/root"))
            .with_budget_manager(BudgetManager(...))
            .build())
    """

    def __init__(self) -> None:
        self._root: Path | None = None
        self._project_root: Path | None = None
        self._persona_detector: PersonaDetector | None = None
        self._skill_resolver: SkillResolver | None = None
        self._budget_manager: BudgetManager | None = None
        self._audit_logger: AuditLogger | None = None
        self._policy_engine: PolicyEngine | None = None
        self._guardian: Guardian | None = None
        self._memory: MemoryStore | None = None

    def with_root(self, root: Path) -> KernelBuilder:
        self._root = root
        return self

    def with_project_root(self, root: Path) -> KernelBuilder:
        self._project_root = root
        return self

    def with_persona_detector(self, pd: PersonaDetector) -> KernelBuilder:
        self._persona_detector = pd
        return self

    def with_skill_resolver(self, sr: SkillResolver) -> KernelBuilder:
        self._skill_resolver = sr
        return self

    def with_budget_manager(self, bm: BudgetManager) -> KernelBuilder:
        self._budget_manager = bm
        return self

    def with_audit_logger(self, al: AuditLogger) -> KernelBuilder:
        self._audit_logger = al
        return self

    def with_policy_engine(self, pe: PolicyEngine) -> KernelBuilder:
        self._policy_engine = pe
        return self

    def with_guardian(self, g: Guardian) -> KernelBuilder:
        self._guardian = g
        return self

    def with_memory(self, m: MemoryStore) -> KernelBuilder:
        self._memory = m
        return self

    def build(self) -> Kernel:
        kwargs: dict[str, Any] = {}
        if self._root is not None:
            kwargs["root"] = self._root
        if self._project_root is not None:
            kwargs["project_root"] = self._project_root
        if self._persona_detector is not None:
            kwargs["persona_detector"] = self._persona_detector
        if self._skill_resolver is not None:
            kwargs["skill_resolver"] = self._skill_resolver
        kernel = Kernel(**kwargs)
        if self._budget_manager is not None:
            kernel.budget = self._budget_manager
        if self._audit_logger is not None:
            kernel.audit = self._audit_logger
        if self._policy_engine is not None:
            kernel.policy = self._policy_engine
        if self._guardian is not None:
            kernel.guardian = self._guardian
        if self._memory is not None:
            # wire memory if applicable
            pass
        return kernel


if __name__ == "__main__":
    k = Kernel()
    print(json.dumps(k.status(), indent=2))
