#!/usr/bin/env python3
"""Agent pool management for the kernel."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from runtime.orchestrator import AgentPool
from runtime.persona import PersonaDetector


class AgentManager:
    """Encapsulates agent spawning and delegation."""

    def __init__(self, root: Path, persona_detector: PersonaDetector) -> None:
        self.root = root
        self.persona = persona_detector
        self.pool = AgentPool(root)

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

    def list_agents(self) -> list[dict[str, Any]]:
        return self.pool.list_agents()
