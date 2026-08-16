"""Tests for runtime/execution_rings.py — graduated privilege hierarchy."""

from __future__ import annotations

import time

from runtime.execution_rings import ExecutionRing, RingManager


class TestRingAssignment:
    def test_high_trust_gets_ring_1(self) -> None:
        mgr = RingManager()
        assert mgr.assign_ring("a1", 0.98) == ExecutionRing.RING_1_PRIVILEGED

    def test_medium_trust_gets_ring_2(self) -> None:
        mgr = RingManager()
        assert mgr.assign_ring("a1", 0.70) == ExecutionRing.RING_2_STANDARD

    def test_low_trust_gets_ring_3(self) -> None:
        mgr = RingManager()
        assert mgr.assign_ring("a1", 0.30) == ExecutionRing.RING_3_SANDBOX

    def test_default_ring_is_sandbox(self) -> None:
        mgr = RingManager()
        assert mgr.get_ring("unknown") == ExecutionRing.RING_3_SANDBOX


class TestRingElevation:
    def test_elevation_grants_higher_privilege(self) -> None:
        mgr = RingManager()
        mgr.assign_ring("a1", 0.70)  # RING_2
        elev = mgr.request_elevation("a1", ExecutionRing.RING_1_PRIVILEGED, ttl_seconds=60)
        assert elev is not None
        assert mgr.get_ring("a1") == ExecutionRing.RING_1_PRIVILEGED

    def test_elevation_expires(self) -> None:
        mgr = RingManager()
        mgr.assign_ring("a1", 0.70)
        elev = mgr.request_elevation("a1", ExecutionRing.RING_1_PRIVILEGED, ttl_seconds=0)
        assert elev is not None
        time.sleep(0.01)
        assert mgr.get_ring("a1") == ExecutionRing.RING_2_STANDARD

    def test_ring_0_requires_high_trust(self) -> None:
        mgr = RingManager()
        mgr.assign_ring("a1", 0.98)
        elev = mgr.request_elevation("a1", ExecutionRing.RING_0_ROOT, trust_score=0.95)
        assert elev is None  # 0.95 < 0.99

    def test_ring_0_granted_with_very_high_trust(self) -> None:
        mgr = RingManager()
        mgr.assign_ring("a1", 0.98)
        elev = mgr.request_elevation("a1", ExecutionRing.RING_0_ROOT, trust_score=0.995)
        assert elev is not None

    def test_no_elevation_to_same_or_lower(self) -> None:
        mgr = RingManager()
        mgr.assign_ring("a1", 0.70)
        elev = mgr.request_elevation("a1", ExecutionRing.RING_3_SANDBOX)
        assert elev is None


class TestRingDemotion:
    def test_demote_on_trust_drop(self) -> None:
        mgr = RingManager()
        mgr.assign_ring("a1", 0.98)  # RING_1
        new_ring = mgr.demote("a1", 0.50)
        assert new_ring == ExecutionRing.RING_3_SANDBOX
        assert mgr.get_ring("a1") == ExecutionRing.RING_3_SANDBOX

    def test_demotion_clears_elevation(self) -> None:
        mgr = RingManager()
        mgr.assign_ring("a1", 0.98)
        mgr.request_elevation("a1", ExecutionRing.RING_0_ROOT, trust_score=0.999)
        mgr.demote("a1", 0.50)
        assert mgr.get_ring("a1") == ExecutionRing.RING_3_SANDBOX


class TestRingCanExecute:
    def test_can_execute_within_ring(self) -> None:
        mgr = RingManager()
        mgr.assign_ring("a1", 0.98)  # RING_1
        assert mgr.can_execute("a1", ExecutionRing.RING_1_PRIVILEGED) is True
        assert mgr.can_execute("a1", ExecutionRing.RING_2_STANDARD) is True

    def test_cannot_execute_above_ring(self) -> None:
        mgr = RingManager()
        mgr.assign_ring("a1", 0.70)  # RING_2
        assert mgr.can_execute("a1", ExecutionRing.RING_1_PRIVILEGED) is False
        assert mgr.can_execute("a1", ExecutionRing.RING_0_ROOT) is False
