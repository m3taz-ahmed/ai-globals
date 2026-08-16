#!/usr/bin/env python3
"""Self-healing runtime with crash recovery (from sol sentinel).

Monitors agent health and automatically respawns crashed agents.
Uses heartbeat tracking and configurable respawn policies.

Usage::

    from runtime.self_healing import HealthMonitor

    monitor = HealthMonitor(heartbeat_timeout=60, max_respawns=3)
    monitor.register("agent-1")
    monitor.heartbeat("agent-1")
    crashed = monitor.check_health()
    for agent_id in crashed:
        monitor.respawn(agent_id)
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class AgentHealth:
    """Health state for a single agent."""

    agent_id: str
    last_heartbeat: float = field(default_factory=time.time)
    respawn_count: int = 0
    status: str = "healthy"  # healthy, stalled, crashed, respawned


@dataclass
class HealthMonitor:
    """Self-healing monitor for agent fleet (from sol sentinel).

    Tracks heartbeats and automatically detects crashed agents.
    Respawn policy limits total respawns per agent.
    """

    heartbeat_timeout: float = 60.0  # seconds without heartbeat = crashed
    max_respawns: int = 3
    respawn_delay: float = 5.0  # delay before respawn
    _agents: dict[str, AgentHealth] = field(default_factory=dict)
    _respawn_callback: Callable[[str], None] | None = None

    def register(self, agent_id: str) -> AgentHealth:
        """Register a new agent for health monitoring."""
        health = AgentHealth(agent_id=agent_id)
        self._agents[agent_id] = health
        return health

    def heartbeat(self, agent_id: str) -> None:
        """Record a heartbeat from an agent."""
        if agent_id in self._agents:
            self._agents[agent_id].last_heartbeat = time.time()
            self._agents[agent_id].status = "healthy"

    def check_health(self) -> list[str]:
        """Check all agents and return list of crashed agent IDs."""
        now = time.time()
        crashed: list[str] = []
        for agent_id, health in self._agents.items():
            if health.status in ("crashed", "respawned"):
                continue
            if now - health.last_heartbeat > self.heartbeat_timeout:
                health.status = "crashed"
                crashed.append(agent_id)
        return crashed

    def can_respawn(self, agent_id: str) -> bool:
        """Check if an agent can be respawned (under max respawns)."""
        health = self._agents.get(agent_id)
        if health is None:
            return False
        return health.respawn_count < self.max_respawns

    def respawn(self, agent_id: str) -> bool:
        """Mark an agent as respawned and increment counter."""
        health = self._agents.get(agent_id)
        if health is None or not self.can_respawn(agent_id):
            return False
        health.respawn_count += 1
        health.status = "respawned"
        health.last_heartbeat = time.time()
        if self._respawn_callback:
            self._respawn_callback(agent_id)
        return True

    def set_respawn_callback(self, callback: Callable[[str], None]) -> None:
        """Set a callback to be called when an agent is respawned."""
        self._respawn_callback = callback

    def get_status(self, agent_id: str) -> AgentHealth | None:
        """Get health status for an agent."""
        return self._agents.get(agent_id)

    def deregister(self, agent_id: str) -> None:
        """Stop monitoring an agent."""
        self._agents.pop(agent_id, None)

    def all_healthy(self) -> bool:
        """Check if all registered agents are healthy."""
        return all(h.status == "healthy" for h in self._agents.values())


if __name__ == "__main__":
    monitor = HealthMonitor(heartbeat_timeout=0.01, max_respawns=2)
    monitor.register("a1")
    time.sleep(0.02)
    crashed = monitor.check_health()
    print(f"Crashed: {crashed}")
    print(f"Can respawn: {monitor.can_respawn('a1')}")
