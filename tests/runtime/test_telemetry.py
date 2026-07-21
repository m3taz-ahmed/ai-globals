"""Tests for telemetry collection."""

from __future__ import annotations

from pathlib import Path

from runtime.kernel import Kernel
from runtime.telemetry import TelemetryCollector, system_metrics


def test_telemetry_records_and_queries(tmp_path: Path) -> None:
    t = TelemetryCollector(tmp_path)
    t.record("action", "Read", "allowed", tokens=10, cost=0.001)
    events = t.query(limit=1)
    assert len(events) == 1
    assert events[0]["action"] == "Read"
    assert events[0]["status"] == "allowed"


def test_telemetry_summary(tmp_path: Path) -> None:
    t = TelemetryCollector(tmp_path)
    t.record("action", "Read", "allowed", tokens=10, cost=0.001)
    summary = t.summary()
    assert summary["total_events"] == 1
    assert summary["total_tokens"] == 10


def test_kernel_records_telemetry(tmp_path: Path) -> None:
    for sub in ("runtime/policies", "state"):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    (tmp_path / "runtime" / "policies" / "default.yaml").write_text(
        "default_action: ask\nrules:\n"
        "  - name: allow-read\n    condition: \"type == 'Read'\"\n    action: allow\n"
    )
    k = Kernel(tmp_path, tmp_path)
    k.act("Read", tokens=5, approved=True)
    events = k.telemetry.query(limit=10)
    assert any(e["action"] == "Read" for e in events)


def test_system_metrics_returns_dict() -> None:
    metrics = system_metrics()
    assert "cpu_percent" in metrics
    assert "memory_percent" in metrics
