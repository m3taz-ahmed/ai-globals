"""Tests for runtime/self_healing.py — self-healing runtime."""

from __future__ import annotations

import time

from runtime.self_healing import HealthMonitor


class TestHealthMonitor:
    def test_register_agent(self) -> None:
        monitor = HealthMonitor()
        health = monitor.register("a1")
        assert health.agent_id == "a1"
        assert health.status == "healthy"

    def test_heartbeat_updates_status(self) -> None:
        monitor = HealthMonitor()
        monitor.register("a1")
        time.sleep(0.01)
        monitor.heartbeat("a1")
        assert monitor.get_status("a1").status == "healthy"

    def test_detect_crashed_agent(self) -> None:
        monitor = HealthMonitor(heartbeat_timeout=0.01)
        monitor.register("a1")
        time.sleep(0.02)
        crashed = monitor.check_health()
        assert "a1" in crashed
        assert monitor.get_status("a1").status == "crashed"

    def test_respawn_increments_count(self) -> None:
        monitor = HealthMonitor(heartbeat_timeout=0.01, max_respawns=2)
        monitor.register("a1")
        time.sleep(0.02)
        monitor.check_health()
        assert monitor.respawn("a1") is True
        assert monitor.get_status("a1").respawn_count == 1

    def test_max_respawns_limit(self) -> None:
        monitor = HealthMonitor(max_respawns=2)
        monitor.register("a1")
        monitor.respawn("a1")
        monitor.respawn("a1")
        assert monitor.can_respawn("a1") is False
        assert monitor.respawn("a1") is False

    def test_respawn_callback_called(self) -> None:
        monitor = HealthMonitor()
        called: list[str] = []
        monitor.set_respawn_callback(lambda aid: called.append(aid))
        monitor.register("a1")
        monitor.respawn("a1")
        assert "a1" in called

    def test_all_healthy(self) -> None:
        monitor = HealthMonitor()
        monitor.register("a1")
        monitor.register("a2")
        assert monitor.all_healthy() is True

    def test_deregister(self) -> None:
        monitor = HealthMonitor()
        monitor.register("a1")
        monitor.deregister("a1")
        assert monitor.get_status("a1") is None
