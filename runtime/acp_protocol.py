#!/usr/bin/env python3
"""ACP (Agent Communication Protocol) support for AI Global OS.

Implements a lightweight ACP-compatible message bus for inter-agent
communication. Agents can discover each other, send messages, and
collaborate on tasks through a standardized protocol.

Features:
- Agent discovery and registration
- Message routing (direct, broadcast, topic-based)
- Request/response patterns with correlation IDs
- Event streaming for real-time updates
- Message queue with persistence

ACP Message Format::

    {
        "id": "msg-uuid",
        "from": "agent-architect",
        "to": "agent-developer",  # or "broadcast" or "topic:reviews"
        "type": "request|response|event|command",
        "action": "review_code",
        "payload": {...},
        "correlation_id": "req-uuid",  # for request/response
        "timestamp": "2026-01-01T00:00:00Z",
        "ttl": 30  # seconds
    }

Usage::

    from runtime.acp_protocol import ACPBroker
    broker = ACPBroker()
    broker.register("agent-arch", capabilities=["review", "design"])
    broker.register("agent-dev", capabilities=["implement"])
    broker.send("agent-arch", "agent-dev", "command", "implement_feature", {"spec": "..."})
    messages = broker.receive("agent-dev")
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class ACPMessage:
    """A single ACP protocol message."""

    id: str = ""
    from_agent: str = ""
    to_agent: str = ""  # specific agent, "broadcast", or "topic:<name>"
    msg_type: str = "event"  # request, response, event, command
    action: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    correlation_id: str = ""
    timestamp: str = ""
    ttl: int = 30

    def __post_init__(self) -> None:
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.correlation_id and self.msg_type == "request":
            self.correlation_id = self.id

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "from": self.from_agent,
            "to": self.to_agent,
            "type": self.msg_type,
            "action": self.action,
            "payload": self.payload,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp,
            "ttl": self.ttl,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ACPMessage:
        return cls(
            id=data.get("id", ""),
            from_agent=data.get("from", ""),
            to_agent=data.get("to", ""),
            msg_type=data.get("type", "event"),
            action=data.get("action", ""),
            payload=data.get("payload", {}),
            correlation_id=data.get("correlation_id", ""),
            timestamp=data.get("timestamp", ""),
            ttl=data.get("ttl", 30),
        )

    @property
    def is_expired(self) -> bool:
        """Check if message has expired based on TTL."""
        if not self.timestamp or self.ttl <= 0:
            return False
        try:
            created = datetime.fromisoformat(self.timestamp)
            elapsed = (datetime.now(timezone.utc) - created).total_seconds()
            return elapsed > self.ttl
        except (ValueError, TypeError):
            return False

    @property
    def is_broadcast(self) -> bool:
        """True if message is a broadcast."""
        return self.to_agent == "broadcast"

    @property
    def is_topic(self) -> bool:
        """True if message is sent to a topic."""
        return self.to_agent.startswith("topic:")

    @property
    def topic_name(self) -> str:
        """Extract topic name if this is a topic message."""
        if self.is_topic:
            return self.to_agent[6:]
        return ""


@dataclass
class AgentInfo:
    """Information about a registered agent."""

    agent_id: str
    capabilities: list[str] = field(default_factory=list)
    status: str = "active"  # active, inactive, busy
    registered_at: str = ""
    last_seen: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class ACPBroker:
    """ACP message broker for inter-agent communication.

    Maintains agent registry and message queues. Messages are persisted
    to disk for durability.
    """

    def __init__(self, state_dir: Path | None = None) -> None:
        self._agents: dict[str, AgentInfo] = {}
        self._queues: dict[str, list[ACPMessage]] = {}
        self._topics: dict[str, list[str]] = {}  # topic -> subscriber agent_ids
        self._state_dir = state_dir
        if state_dir:
            state_dir.mkdir(parents=True, exist_ok=True)
            self._load_state()

    def register(self, agent_id: str, capabilities: list[str] | None = None, metadata: dict[str, Any] | None = None) -> AgentInfo:
        """Register an agent in the broker."""
        now = datetime.now(timezone.utc).isoformat()
        if agent_id in self._agents:
            # Update existing
            info = self._agents[agent_id]
            info.capabilities = capabilities or info.capabilities
            info.status = "active"
            info.last_seen = now
            if metadata:
                info.metadata.update(metadata)
        else:
            info = AgentInfo(
                agent_id=agent_id,
                capabilities=capabilities or [],
                status="active",
                registered_at=now,
                last_seen=now,
                metadata=metadata or {},
            )
            self._agents[agent_id] = info
            self._queues[agent_id] = []
        self._save_state()
        return info

    def unregister(self, agent_id: str) -> bool:
        """Unregister an agent."""
        if agent_id not in self._agents:
            return False
        del self._agents[agent_id]
        self._queues.pop(agent_id, None)
        # Remove from all topic subscriptions
        for subs in self._topics.values():
            if agent_id in subs:
                subs.remove(agent_id)
        self._save_state()
        return True

    def subscribe(self, agent_id: str, topic: str) -> bool:
        """Subscribe an agent to a topic."""
        if agent_id not in self._agents:
            return False
        if topic not in self._topics:
            self._topics[topic] = []
        if agent_id not in self._topics[topic]:
            self._topics[topic].append(agent_id)
        self._save_state()
        return True

    def unsubscribe(self, agent_id: str, topic: str) -> bool:
        """Unsubscribe an agent from a topic."""
        if topic not in self._topics:
            return False
        if agent_id not in self._topics[topic]:
            return False
        self._topics[topic].remove(agent_id)
        self._save_state()
        return True

    def send(
        self,
        from_agent: str,
        to_agent: str,
        msg_type: str = "event",
        action: str = "",
        payload: dict[str, Any] | None = None,
        correlation_id: str = "",
        ttl: int = 30,
    ) -> ACPMessage:
        """Send a message to an agent, broadcast, or topic."""
        msg = ACPMessage(
            from_agent=from_agent,
            to_agent=to_agent,
            msg_type=msg_type,
            action=action,
            payload=payload or {},
            correlation_id=correlation_id,
            ttl=ttl,
        )
        if msg.is_broadcast:
            # Deliver to all active agents except sender
            for agent_id in self._agents:
                if agent_id != from_agent:
                    self._queues.setdefault(agent_id, []).append(msg)
        elif msg.is_topic:
            # Deliver to topic subscribers
            topic = msg.topic_name
            for agent_id in self._topics.get(topic, []):
                if agent_id != from_agent:
                    self._queues.setdefault(agent_id, []).append(msg)
        else:
            # Direct message
            if to_agent not in self._agents:
                raise ValueError(f"Recipient agent not registered: {to_agent}")
            self._queues.setdefault(to_agent, []).append(msg)
        self._save_state()
        return msg

    def receive(self, agent_id: str, max_messages: int = 100) -> list[ACPMessage]:
        """Receive pending messages for an agent."""
        if agent_id not in self._agents:
            return []
        queue = self._queues.get(agent_id, [])
        # Filter out expired messages
        valid = [m for m in queue if not m.is_expired]
        messages = valid[:max_messages]
        # Remove received messages from queue
        self._queues[agent_id] = valid[max_messages:]
        # Update last_seen
        self._agents[agent_id].last_seen = datetime.now(timezone.utc).isoformat()
        self._save_state()
        return messages

    def peek(self, agent_id: str) -> list[ACPMessage]:
        """Peek at messages without removing them."""
        if agent_id not in self._agents:
            return []
        queue = self._queues.get(agent_id, [])
        return [m for m in queue if not m.is_expired]

    def request(
        self,
        from_agent: str,
        to_agent: str,
        action: str,
        payload: dict[str, Any] | None = None,
        ttl: int = 30,
    ) -> str:
        """Send a request message and return the correlation ID."""
        msg = self.send(
            from_agent=from_agent,
            to_agent=to_agent,
            msg_type="request",
            action=action,
            payload=payload or {},
            ttl=ttl,
        )
        return msg.correlation_id

    def respond(
        self,
        from_agent: str,
        to_agent: str,
        correlation_id: str,
        payload: dict[str, Any] | None = None,
    ) -> ACPMessage:
        """Send a response to a request."""
        return self.send(
            from_agent=from_agent,
            to_agent=to_agent,
            msg_type="response",
            action="response",
            payload=payload or {},
            correlation_id=correlation_id,
        )

    def discover(self, capability: str | None = None) -> list[AgentInfo]:
        """Discover agents, optionally filtered by capability."""
        if capability is None:
            return list(self._agents.values())
        return [
            info for info in self._agents.values()
            if capability in info.capabilities and info.status == "active"
        ]

    def list_agents(self) -> list[dict[str, Any]]:
        """List all registered agents."""
        return [
            {
                "agent_id": info.agent_id,
                "capabilities": info.capabilities,
                "status": info.status,
                "registered_at": info.registered_at,
                "last_seen": info.last_seen,
                "pending_messages": len(self._queues.get(info.agent_id, [])),
            }
            for info in self._agents.values()
        ]

    def list_topics(self) -> dict[str, list[str]]:
        """List all topics and their subscribers."""
        return dict(self._topics)

    def get_agent_info(self, agent_id: str) -> AgentInfo | None:
        """Get info about a specific agent."""
        return self._agents.get(agent_id)

    def set_agent_status(self, agent_id: str, status: str) -> bool:
        """Update an agent's status."""
        if agent_id not in self._agents:
            return False
        self._agents[agent_id].status = status
        self._save_state()
        return True

    def clear_queue(self, agent_id: str) -> int:
        """Clear an agent's message queue. Returns count of cleared messages."""
        if agent_id not in self._queues:
            return 0
        count = len(self._queues[agent_id])
        self._queues[agent_id] = []
        self._save_state()
        return count

    def _save_state(self) -> None:
        """Save broker state to disk."""
        if not self._state_dir:
            return
        state = {
            "agents": {
                aid: {
                    "agent_id": info.agent_id,
                    "capabilities": info.capabilities,
                    "status": info.status,
                    "registered_at": info.registered_at,
                    "last_seen": info.last_seen,
                    "metadata": info.metadata,
                }
                for aid, info in self._agents.items()
            },
            "queues": {
                aid: [m.to_dict() for m in queue]
                for aid, queue in self._queues.items()
            },
            "topics": self._topics,
        }
        (self._state_dir / "acp_state.json").write_text(
            json.dumps(state, indent=2), encoding="utf-8",
        )

    def _load_state(self) -> None:
        """Load broker state from disk."""
        path = self._state_dir / "acp_state.json" if self._state_dir else None
        if not path or not path.exists():
            return
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
            for aid, data in state.get("agents", {}).items():
                self._agents[aid] = AgentInfo(
                    agent_id=data["agent_id"],
                    capabilities=data.get("capabilities", []),
                    status=data.get("status", "active"),
                    registered_at=data.get("registered_at", ""),
                    last_seen=data.get("last_seen", ""),
                    metadata=data.get("metadata", {}),
                )
            for aid, msgs in state.get("queues", {}).items():
                self._queues[aid] = [ACPMessage.from_dict(m) for m in msgs]
            self._topics = state.get("topics", {})
        except (json.JSONDecodeError, KeyError):
            pass

    def status(self) -> dict[str, Any]:
        """Return broker status summary."""
        return {
            "total_agents": len(self._agents),
            "active_agents": sum(1 for a in self._agents.values() if a.status == "active"),
            "total_topics": len(self._topics),
            "total_pending_messages": sum(len(q) for q in self._queues.values()),
        }


if __name__ == "__main__":
    import sys
    state_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    broker = ACPBroker(state_dir)
    print(json.dumps(broker.status(), indent=2))
