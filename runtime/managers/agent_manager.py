#!/usr/bin/env python3
"""Agent pool management for the kernel."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from runtime.orchestrator import AgentPool
from runtime.persona import PersonaDetector
from runtime.self_healing import HealthMonitor


class AgentManager:
    """Encapsulates agent spawning and delegation."""

    def __init__(self, root: Path, persona_detector: PersonaDetector) -> None:
        self.root = root
        self.persona = persona_detector
        self.pool = AgentPool(root)
        self.health = HealthMonitor()

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
        self.health.register(agent_id)
        self.health.heartbeat(agent_id)
        return {
            "ok": True,
            "id": agent.id,
            "persona": agent.persona,
            "personas": agent.personas,
            "lords": agent.lords,
            "scope": agent.scope,
        }

    def delegate(self, agent_id: str, action_type: str, **kwargs: Any) -> dict[str, Any]:
        result = self.pool.delegate(agent_id, action_type, **kwargs)
        # Record a heartbeat after agent activity so the health monitor
        # can track liveness without a background thread.
        self.health.heartbeat(agent_id)
        return result

    def list_agents(self) -> list[dict[str, Any]]:
        return self.pool.list_agents()

    def check_health(self) -> list[str]:
        """Check all registered agents and return list of crashed agent IDs.

        Short alias for :meth:`check_agents_health` matching the requested API.
        """
        return self.health.check_health()

    def check_agents_health(self) -> list[str]:
        """Check all registered agents and return list of crashed agent IDs."""
        return self.health.check_health()

    def respawn_agent(self, agent_id: str) -> dict[str, Any]:
        """Re-create a crashed agent using its last known configuration.

        Returns a dict with ``ok`` and either the new agent info or an error.
        """
        agent = self.pool.get(agent_id)
        if agent is None:
            return {"ok": False, "error": f"Agent '{agent_id}' not found"}
        if not self.health.can_respawn(agent_id):
            return {"ok": False, "error": f"Agent '{agent_id}' exceeded respawn limit"}
        personas = agent.personas
        scope = agent.scope
        lords = agent.lords
        project_root = agent.project_root
        self.pool.register(agent_id, personas, scope, project_root, lords=lords)
        self.health.respawn(agent_id)
        status = self.health.get_status(agent_id)
        return {
            "ok": True,
            "id": agent_id,
            "persona": personas[0] if personas else "ARCH",
            "respawn_count": status.respawn_count if status else 0,
        }
