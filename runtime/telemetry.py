"""Telemetry and observability collector for AI Global OS."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class TelemetryEvent:
    """A single telemetry event."""

    timestamp: str
    type: str
    action: str
    project: str
    status: str
    tokens: int
    cost: float
    metadata: dict[str, Any]


class TelemetryCollector:
    """Collects and persists runtime telemetry events."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.log_path = project_root / "state" / "telemetry.jsonl"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        event_type: str,
        action: str,
        status: str,
        tokens: int = 0,
        cost: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        event = TelemetryEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            type=event_type,
            action=action,
            project=str(self.project_root),
            status=status,
            tokens=tokens,
            cost=cost,
            metadata=metadata or {},
        )
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(event), default=str) + "\n")

    def query(self, limit: int = 100, event_type: str | None = None) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        if not self.log_path.exists():
            return events
        with self.log_path.open("r", encoding="utf-8") as f:
            for line in reversed(f.readlines()):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event_type and data.get("type") != event_type:
                    continue
                events.append(data)
                if len(events) >= limit:
                    break
        return events

    def summary(self) -> dict[str, Any]:
        total_events = 0
        by_type: dict[str, int] = {}
        by_status: dict[str, int] = {}
        total_tokens = 0
        total_cost = 0.0
        if self.log_path.exists():
            with self.log_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    total_events += 1
                    by_type[data.get("type", "unknown")] = by_type.get(data.get("type", "unknown"), 0) + 1
                    by_status[data.get("status", "unknown")] = by_status.get(data.get("status", "unknown"), 0) + 1
                    total_tokens += data.get("tokens", 0)
                    total_cost += data.get("cost", 0.0)
        return {
            "total_events": total_events,
            "by_type": by_type,
            "by_status": by_status,
            "total_tokens": total_tokens,
            "total_cost": total_cost,
        }


def system_metrics() -> dict[str, Any]:
    """Return basic system metrics."""
    try:
        import psutil  # type: ignore[import-untyped]

        mem = psutil.virtual_memory()
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": mem.percent,
            "memory_used_mb": mem.used // (1024 * 1024),
            "memory_total_mb": mem.total // (1024 * 1024),
        }
    except Exception:
        return {
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "memory_used_mb": 0,
            "memory_total_mb": 0,
        }
