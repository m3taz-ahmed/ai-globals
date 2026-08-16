#!/usr/bin/env python3
"""Execution Rings — graduated privilege hierarchy for AI agents.

Inspired by Microsoft's agent-governance-toolkit. Hardware-inspired
privilege model with 4 rings, trust-score-based assignment, sudo
elevation with TTL, and real-time demotion on trust drops.

Usage::

    from runtime.execution_rings import ExecutionRing, RingManager

    mgr = RingManager()
    ring = mgr.assign_ring(agent_id="a1", trust_score=0.95)
    assert ring == ExecutionRing.RING_1_PRIVILEGED
    elev = mgr.request_elevation("a1", ExecutionRing.RING_0_ROOT, ttl_seconds=300)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import IntEnum


class ExecutionRing(IntEnum):
    """4 privilege levels (hardware-inspired)."""

    RING_0_ROOT = 0          # Hypervisor config (requires SRE Witness)
    RING_1_PRIVILEGED = 1    # Non-reversible actions (trust > 0.95 + consensus)
    RING_2_STANDARD = 2      # Reversible actions (trust > 0.60)
    RING_3_SANDBOX = 3       # Read-only / research (default)


@dataclass
class RingElevation:
    """Temporary privilege escalation with TTL."""

    agent_id: str
    from_ring: ExecutionRing
    to_ring: ExecutionRing
    granted_at: float
    expires_at: float
    reason: str = ""

    @property
    def expired(self) -> bool:
        return time.time() > self.expires_at


@dataclass
class RingManager:
    """Manages execution ring assignment and elevation.

    Ring assignment is based on trust score:
    - trust >= 0.95 → RING_1_PRIVILEGED
    - trust >= 0.60 → RING_2_STANDARD
    - trust < 0.60  → RING_3_SANDBOX
    RING_0_ROOT requires explicit elevation with SRE witness.
    """

    _agent_rings: dict[str, ExecutionRing] = field(default_factory=dict)
    _elevations: dict[str, RingElevation] = field(default_factory=dict)
    ring_1_threshold: float = 0.95
    ring_2_threshold: float = 0.60

    def assign_ring(self, agent_id: str, trust_score: float) -> ExecutionRing:
        """Assign a ring based on trust score."""
        if trust_score >= self.ring_1_threshold:
            ring = ExecutionRing.RING_1_PRIVILEGED
        elif trust_score >= self.ring_2_threshold:
            ring = ExecutionRing.RING_2_STANDARD
        else:
            ring = ExecutionRing.RING_3_SANDBOX
        self._agent_rings[agent_id] = ring
        return ring

    def get_ring(self, agent_id: str) -> ExecutionRing:
        """Get current effective ring (considering active elevations)."""
        elev = self._elevations.get(agent_id)
        if elev and not elev.expired:
            return elev.to_ring
        if elev and elev.expired:
            del self._elevations[agent_id]
        return self._agent_rings.get(agent_id, ExecutionRing.RING_3_SANDBOX)

    def request_elevation(
        self,
        agent_id: str,
        target_ring: ExecutionRing,
        ttl_seconds: int = 300,
        reason: str = "",
        trust_score: float | None = None,
    ) -> RingElevation | None:
        """Request temporary privilege escalation with TTL."""
        current = self.get_ring(agent_id)
        if target_ring >= current:
            return None  # Not an elevation
        # RING_0_ROOT requires very high trust
        if target_ring == ExecutionRing.RING_0_ROOT and trust_score is not None and trust_score < 0.99:
            return None
        now = time.time()
        elev = RingElevation(
            agent_id=agent_id,
            from_ring=current,
            to_ring=target_ring,
            granted_at=now,
            expires_at=now + ttl_seconds,
            reason=reason,
        )
        self._elevations[agent_id] = elev
        return elev

    def demote(self, agent_id: str, trust_score: float) -> ExecutionRing:
        """Real-time demotion on trust drop."""
        new_ring = self.assign_ring(agent_id, trust_score)
        # Clear any active elevation that grants higher privilege than new ring
        elev = self._elevations.get(agent_id)
        if elev and not elev.expired and elev.to_ring < new_ring:
            del self._elevations[agent_id]
        return new_ring

    def can_execute(self, agent_id: str, required_ring: ExecutionRing) -> bool:
        """Check if agent's current ring allows the operation."""
        return self.get_ring(agent_id) <= required_ring

    def clear_elevation(self, agent_id: str) -> None:
        """Manually clear an active elevation."""
        self._elevations.pop(agent_id, None)


if __name__ == "__main__":
    mgr = RingManager()
    print(f"High trust: {mgr.assign_ring('a1', 0.98)}")
    print(f"Medium trust: {mgr.assign_ring('a2', 0.70)}")
    print(f"Low trust: {mgr.assign_ring('a3', 0.30)}")
