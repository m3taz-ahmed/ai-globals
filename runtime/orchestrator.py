"""Sub-agent orchestration and kernel pool."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from runtime.kernel import Kernel


@dataclass
class SubAgent:
    """A sub-agent descriptor."""

    id: str
    persona: str
    scope: list[str]
    project_root: Path
    kernel: Kernel = field(compare=False)


class AgentPool:
    """Pool of isolated sub-agent kernels with separate budgets/policies."""

    def __init__(self, os_root: Path) -> None:
        self.os_root = os_root
        self._agents: dict[str, SubAgent] = {}
        self._lock = threading.Lock()

    def register(
        self,
        agent_id: str,
        persona: str,
        scope: list[str],
        project_root: Path | None = None,
    ) -> SubAgent:
        from runtime.kernel import Kernel

        root = project_root or self.os_root / "state" / "agents" / agent_id
        root.mkdir(parents=True, exist_ok=True)
        for sub in ("runtime/policies", "state", "brain"):
            (root / sub).mkdir(parents=True, exist_ok=True)
        kernel = Kernel(self.os_root, root)
        agent = SubAgent(id=agent_id, persona=persona, scope=scope, project_root=root, kernel=kernel)
        with self._lock:
            self._agents[agent_id] = agent
        return agent

    def get(self, agent_id: str) -> SubAgent | None:
        with self._lock:
            return self._agents.get(agent_id)

    def delegate(self, agent_id: str, action_type: str, **kwargs: Any) -> dict[str, Any]:
        agent = self.get(agent_id)
        if not agent:
            return {"ok": False, "error": f"Agent '{agent_id}' not found"}
        if action_type not in agent.scope:
            return {"ok": False, "error": f"Action '{action_type}' outside agent '{agent_id}' scope"}
        kwargs.setdefault("approved", True)
        return agent.kernel.act(action_type, **kwargs)

    def synchronize(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return {
                agent_id: {
                    "persona": agent.persona,
                    "scope": agent.scope,
                    "status": agent.kernel.status(),
                }
                for agent_id, agent in self._agents.items()
            }

    def list_agents(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                {"id": a.id, "persona": a.persona, "scope": a.scope, "project_root": str(a.project_root)}
                for a in self._agents.values()
            ]
