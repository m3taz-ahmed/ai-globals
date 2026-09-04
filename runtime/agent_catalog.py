"""Allowlist catalog of permitted AI agents, flows, and models.

Inspired by GitLab Duo's central agent/flow catalog: a single source of
truth for which agents may run, which flows they may execute, and which
models they may call. RBAC-gated via status flags and explicit allowlists.

Usage::

    from runtime.agent_catalog import AgentCatalog, CatalogAgent, AgentStatus

    catalog = AgentCatalog()
    catalog.register_agent(CatalogAgent(
        agent_id="coder", name="Coder",
        status=AgentStatus.ALLOWED,
        allowed_flows=["code-gen"], allowed_models=["gpt-4o"],
    ))
    assert catalog.is_agent_allowed("coder") is True
"""

from __future__ import annotations

import copy
import threading
from dataclasses import dataclass, field
from enum import Enum


class AgentStatus(str, Enum):
    """Permit status for an agent in the catalog."""

    ALLOWED = "allowed"
    BLOCKED = "blocked"
    DEPRECATED = "deprecated"


class ModelTier(str, Enum):
    """Cost/capability tier for a model."""

    FRONTIER = "frontier"
    STANDARD = "standard"
    LOCAL = "local"


@dataclass
class CatalogAgent:
    """A registered AI agent and its allowed flows/models."""

    agent_id: str
    name: str
    status: AgentStatus
    allowed_flows: list[str] = field(default_factory=list)
    allowed_models: list[str] = field(default_factory=list)
    owner: str = ""


@dataclass
class CatalogFlow:
    """A registered flow (multi-step agent procedure).

    ``allowed_agents`` is enforced by
    :meth:`AgentCatalog.is_flow_allowed_for_agent` in addition to the
    agent-side ``CatalogAgent.allowed_flows`` allowlist: when non-empty,
    the agent must be listed here AND the flow must be listed on the
    agent. An empty list means "no flow-side restriction".
    """

    flow_id: str
    name: str
    allowed_agents: list[str] = field(default_factory=list)
    max_steps: int = 50


@dataclass
class CatalogModel:
    """A registered LLM model and its tier."""

    model_id: str
    provider: str
    tier: ModelTier
    max_tokens: int = 200000


class AgentCatalog:
    """Thread-safe allowlist catalog for agents, flows, and models.

    All mutations are guarded by an internal lock so the catalog can be
    shared across threads (e.g. kernel + MCP server).
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._agents: dict[str, CatalogAgent] = {}
        self._flows: dict[str, CatalogFlow] = {}
        self._models: dict[str, CatalogModel] = {}

    # -- registration ----------------------------------------------------

    def register_agent(self, agent: CatalogAgent) -> None:
        """Register or replace an agent by its ``agent_id``."""
        with self._lock:
            self._agents[agent.agent_id] = agent

    def register_flow(self, flow: CatalogFlow) -> None:
        """Register or replace a flow by its ``flow_id``."""
        with self._lock:
            self._flows[flow.flow_id] = flow

    def register_model(self, model: CatalogModel) -> None:
        """Register or replace a model by its ``model_id``."""
        with self._lock:
            self._models[model.model_id] = model

    # -- lookups ---------------------------------------------------------

    def get_agent(self, agent_id: str) -> CatalogAgent | None:
        """Return the agent with ``agent_id`` or ``None``."""
        with self._lock:
            return self._agents.get(agent_id)

    def get_flow(self, flow_id: str) -> CatalogFlow | None:
        """Return the flow with ``flow_id`` or ``None``."""
        with self._lock:
            return self._flows.get(flow_id)

    def get_model(self, model_id: str) -> CatalogModel | None:
        """Return the model with ``model_id`` or ``None``."""
        with self._lock:
            return self._models.get(model_id)

    # -- permission checks ----------------------------------------------

    def is_agent_allowed(self, agent_id: str) -> bool:
        """True if the agent exists and its status is ``ALLOWED``."""
        with self._lock:
            agent = self._agents.get(agent_id)
            return agent is not None and agent.status == AgentStatus.ALLOWED

    def is_flow_allowed_for_agent(self, agent_id: str, flow_id: str) -> bool:
        """True if the agent is allowed and the flow is in its allowlist."""
        with self._lock:
            agent = self._agents.get(agent_id)
            if agent is None or agent.status != AgentStatus.ALLOWED:
                return False
            if flow_id not in agent.allowed_flows:
                return False
            flow = self._flows.get(flow_id)
            if flow is None:
                return False
            return not flow.allowed_agents or agent_id in flow.allowed_agents

    def is_model_allowed_for_agent(self, agent_id: str, model_id: str) -> bool:
        """True if the agent is allowed and the model is in its allowlist."""
        with self._lock:
            agent = self._agents.get(agent_id)
            if agent is None or agent.status != AgentStatus.ALLOWED:
                return False
            if model_id not in agent.allowed_models:
                return False
            return model_id in self._models

    # -- listings --------------------------------------------------------

    def list_agents(self, status: AgentStatus | None = None) -> list[CatalogAgent]:
        """List agents, optionally filtered by status."""
        with self._lock:
            agents = [copy.deepcopy(a) for a in self._agents.values()]
        if status is None:
            return agents
        return [a for a in agents if a.status == status]

    def list_flows(self) -> list[CatalogFlow]:
        """List all registered flows."""
        with self._lock:
            return [copy.deepcopy(f) for f in self._flows.values()]

    def list_models(self, tier: ModelTier | None = None) -> list[CatalogModel]:
        """List models, optionally filtered by tier."""
        with self._lock:
            models = [copy.deepcopy(m) for m in self._models.values()]
        if tier is None:
            return models
        return [m for m in models if m.tier == tier]

    # -- mutations -------------------------------------------------------

    def block_agent(self, agent_id: str) -> bool:
        """Set an agent's status to ``BLOCKED``. Returns False if not found."""
        with self._lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return False
            agent.status = AgentStatus.BLOCKED
            return True

    def clear(self) -> None:
        """Remove all agents, flows, and models."""
        with self._lock:
            self._agents.clear()
            self._flows.clear()
            self._models.clear()


__all__ = [
    "AgentCatalog",
    "AgentStatus",
    "CatalogAgent",
    "CatalogFlow",
    "CatalogModel",
    "ModelTier",
]
