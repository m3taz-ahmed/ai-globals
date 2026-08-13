"""Tests for runtime/acp_protocol.py — ACP inter-agent communication."""

from __future__ import annotations

from pathlib import Path

import pytest

from runtime.acp_protocol import (
    ACPBroker,
    ACPMessage,
    AgentInfo,
)


class TestACPMessage:
    """Tests for ACPMessage."""

    def test_defaults(self) -> None:
        msg = ACPMessage()
        assert msg.id != ""  # auto-generated
        assert msg.timestamp != ""  # auto-generated
        assert msg.msg_type == "event"

    def test_request_generates_correlation_id(self) -> None:
        msg = ACPMessage(msg_type="request")
        assert msg.correlation_id == msg.id

    def test_to_dict_and_from_dict(self) -> None:
        msg = ACPMessage(
            from_agent="a1",
            to_agent="a2",
            msg_type="command",
            action="do_thing",
            payload={"x": 1},
        )
        d = msg.to_dict()
        restored = ACPMessage.from_dict(d)
        assert restored.from_agent == "a1"
        assert restored.to_agent == "a2"
        assert restored.action == "do_thing"
        assert restored.payload == {"x": 1}

    def test_is_broadcast(self) -> None:
        msg = ACPMessage(to_agent="broadcast")
        assert msg.is_broadcast is True

    def test_is_topic(self) -> None:
        msg = ACPMessage(to_agent="topic:reviews")
        assert msg.is_topic is True
        assert msg.topic_name == "reviews"

    def test_not_topic(self) -> None:
        msg = ACPMessage(to_agent="agent-1")
        assert msg.is_topic is False
        assert msg.topic_name == ""

    def test_is_expired_false_no_timestamp(self) -> None:
        msg = ACPMessage(ttl=1)
        msg.timestamp = ""
        assert msg.is_expired is False

    def test_is_expired_with_old_timestamp(self) -> None:
        msg = ACPMessage(ttl=1)
        msg.timestamp = "2020-01-01T00:00:00+00:00"
        assert msg.is_expired is True

    def test_is_expired_with_recent_timestamp(self) -> None:
        msg = ACPMessage(ttl=3600)
        from datetime import datetime, timezone
        msg.timestamp = datetime.now(timezone.utc).isoformat()
        assert msg.is_expired is False


class TestAgentInfo:
    """Tests for AgentInfo."""

    def test_defaults(self) -> None:
        info = AgentInfo(agent_id="a1")
        assert info.capabilities == []
        assert info.status == "active"
        assert info.metadata == {}


class TestACPBroker:
    """Tests for ACPBroker."""

    def test_register_agent(self) -> None:
        broker = ACPBroker()
        info = broker.register("a1", ["review", "design"])
        assert info.agent_id == "a1"
        assert "review" in info.capabilities
        assert info.status == "active"

    def test_register_duplicate_updates(self) -> None:
        broker = ACPBroker()
        broker.register("a1", ["review"])
        info = broker.register("a1", ["review", "design"])
        assert "design" in info.capabilities

    def test_unregister_agent(self) -> None:
        broker = ACPBroker()
        broker.register("a1")
        assert broker.unregister("a1") is True
        assert broker.get_agent_info("a1") is None

    def test_unregister_nonexistent(self) -> None:
        broker = ACPBroker()
        assert broker.unregister("nonexistent") is False

    def test_send_direct_message(self) -> None:
        broker = ACPBroker()
        broker.register("a1")
        broker.register("a2")
        broker.send("a1", "a2", "event", "notify", {"data": 1})
        messages = broker.receive("a2")
        assert len(messages) == 1
        assert messages[0].action == "notify"
        assert messages[0].from_agent == "a1"

    def test_send_to_unregistered_agent(self) -> None:
        broker = ACPBroker()
        broker.register("a1")
        with pytest.raises(ValueError, match="not registered"):
            broker.send("a1", "nonexistent", "event", "test")

    def test_send_broadcast(self) -> None:
        broker = ACPBroker()
        broker.register("a1")
        broker.register("a2")
        broker.register("a3")
        broker.send("a1", "broadcast", "event", "announcement")
        # a2 and a3 should receive, a1 should not
        assert len(broker.receive("a2")) == 1
        assert len(broker.receive("a3")) == 1
        assert len(broker.receive("a1")) == 0

    def test_send_topic_message(self) -> None:
        broker = ACPBroker()
        broker.register("a1")
        broker.register("a2")
        broker.register("a3")
        broker.subscribe("a2", "reviews")
        broker.subscribe("a3", "reviews")
        broker.send("a1", "topic:reviews", "event", "code_review", {"file": "test.py"})
        assert len(broker.receive("a2")) == 1
        assert len(broker.receive("a3")) == 1

    def test_send_topic_no_subscribers(self) -> None:
        broker = ACPBroker()
        broker.register("a1")
        # Should not raise even with no subscribers
        broker.send("a1", "topic:nonexistent", "event", "test")

    def test_subscribe(self) -> None:
        broker = ACPBroker()
        broker.register("a1")
        assert broker.subscribe("a1", "reviews") is True
        topics = broker.list_topics()
        assert "reviews" in topics
        assert "a1" in topics["reviews"]

    def test_subscribe_nonexistent_agent(self) -> None:
        broker = ACPBroker()
        assert broker.subscribe("nonexistent", "reviews") is False

    def test_unsubscribe(self) -> None:
        broker = ACPBroker()
        broker.register("a1")
        broker.subscribe("a1", "reviews")
        assert broker.unsubscribe("a1", "reviews") is True
        assert "a1" not in broker.list_topics().get("reviews", [])

    def test_unsubscribe_not_subscribed(self) -> None:
        broker = ACPBroker()
        broker.register("a1")
        assert broker.unsubscribe("a1", "reviews") is False

    def test_receive_empty(self) -> None:
        broker = ACPBroker()
        broker.register("a1")
        assert broker.receive("a1") == []

    def test_receive_nonexistent_agent(self) -> None:
        broker = ACPBroker()
        assert broker.receive("nonexistent") == []

    def test_receive_removes_messages(self) -> None:
        broker = ACPBroker()
        broker.register("a1")
        broker.register("a2")
        broker.send("a1", "a2", "event", "test")
        first = broker.receive("a2")
        assert len(first) == 1
        second = broker.receive("a2")
        assert len(second) == 0

    def test_peek_does_not_remove(self) -> None:
        broker = ACPBroker()
        broker.register("a1")
        broker.register("a2")
        broker.send("a1", "a2", "event", "test")
        peeked = broker.peek("a2")
        assert len(peeked) == 1
        # Still there
        assert len(broker.peek("a2")) == 1

    def test_request_response_pattern(self) -> None:
        broker = ACPBroker()
        broker.register("a1")
        broker.register("a2")
        # a1 sends request
        corr_id = broker.request("a1", "a2", "review_code", {"file": "test.py"})
        # a2 receives and responds
        messages = broker.receive("a2")
        assert len(messages) == 1
        assert messages[0].msg_type == "request"
        assert messages[0].correlation_id == corr_id
        # a2 responds
        broker.respond("a2", "a1", corr_id, {"approved": True})
        # a1 receives response
        responses = broker.receive("a1")
        assert len(responses) == 1
        assert responses[0].msg_type == "response"
        assert responses[0].correlation_id == corr_id

    def test_discover_all(self) -> None:
        broker = ACPBroker()
        broker.register("a1", ["review"])
        broker.register("a2", ["implement"])
        agents = broker.discover()
        assert len(agents) == 2

    def test_discover_by_capability(self) -> None:
        broker = ACPBroker()
        broker.register("a1", ["review", "design"])
        broker.register("a2", ["implement"])
        reviewers = broker.discover("review")
        assert len(reviewers) == 1
        assert reviewers[0].agent_id == "a1"

    def test_discover_no_match(self) -> None:
        broker = ACPBroker()
        broker.register("a1", ["review"])
        assert broker.discover("nonexistent_capability") == []

    def test_list_agents(self) -> None:
        broker = ACPBroker()
        broker.register("a1", ["review"])
        broker.register("a2", ["implement"])
        agents = broker.list_agents()
        assert len(agents) == 2
        assert agents[0]["pending_messages"] == 0

    def test_list_topics(self) -> None:
        broker = ACPBroker()
        broker.register("a1")
        broker.subscribe("a1", "reviews")
        broker.subscribe("a1", "deployments")
        topics = broker.list_topics()
        assert "reviews" in topics
        assert "deployments" in topics

    def test_set_agent_status(self) -> None:
        broker = ACPBroker()
        broker.register("a1")
        assert broker.set_agent_status("a1", "busy") is True
        assert broker.get_agent_info("a1").status == "busy"

    def test_set_agent_status_nonexistent(self) -> None:
        broker = ACPBroker()
        assert broker.set_agent_status("nonexistent", "busy") is False

    def test_clear_queue(self) -> None:
        broker = ACPBroker()
        broker.register("a1")
        broker.register("a2")
        broker.send("a1", "a2", "event", "test1")
        broker.send("a1", "a2", "event", "test2")
        count = broker.clear_queue("a2")
        assert count == 2
        assert broker.receive("a2") == []

    def test_clear_queue_empty(self) -> None:
        broker = ACPBroker()
        broker.register("a1")
        assert broker.clear_queue("a1") == 0

    def test_status(self) -> None:
        broker = ACPBroker()
        broker.register("a1")
        broker.register("a2")
        broker.subscribe("a1", "reviews")
        broker.send("a1", "a2", "event", "test")
        status = broker.status()
        assert status["total_agents"] == 2
        assert status["total_topics"] == 1
        assert status["total_pending_messages"] == 1

    def test_persistence(self, tmp_path: Path) -> None:
        broker = ACPBroker(tmp_path / "state")
        broker.register("a1", ["review"])
        broker.register("a2", ["implement"])
        broker.send("a1", "a2", "event", "test")
        # Create new broker from same state
        broker2 = ACPBroker(tmp_path / "state")
        assert broker2.get_agent_info("a1") is not None
        assert broker2.get_agent_info("a2") is not None
        messages = broker2.receive("a2")
        assert len(messages) == 1

    def test_persistence_topics(self, tmp_path: Path) -> None:
        broker = ACPBroker(tmp_path / "state")
        broker.register("a1")
        broker.subscribe("a1", "reviews")
        broker2 = ACPBroker(tmp_path / "state")
        topics = broker2.list_topics()
        assert "reviews" in topics
        assert "a1" in topics["reviews"]
