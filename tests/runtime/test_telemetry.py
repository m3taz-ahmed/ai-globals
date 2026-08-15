"""Tests for telemetry collection."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

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


def test_system_metrics_success_path() -> None:
    """Cover the success path of system_metrics() when psutil is available."""
    import sys
    from unittest.mock import MagicMock

    mock_psutil = MagicMock()
    mock_psutil.cpu_percent.return_value = 42.5
    mock_mem = MagicMock()
    mock_mem.percent = 75.0
    mock_mem.used = 1024 * 1024 * 100  # 100 MB
    mock_mem.total = 1024 * 1024 * 200  # 200 MB
    mock_psutil.virtual_memory.return_value = mock_mem
    sys.modules["psutil"] = mock_psutil
    try:
        metrics = system_metrics()
    finally:
        sys.modules.pop("psutil", None)
    assert metrics["cpu_percent"] == 42.5
    assert metrics["memory_percent"] == 75.0
    assert metrics["memory_used_mb"] == 100
    assert metrics["memory_total_mb"] == 200


# ---------------------------------------------------------------------------
# query() — line 59 (log file doesn't exist returns empty list)
# ---------------------------------------------------------------------------

def test_query_returns_empty_when_no_log(tmp_path: Path) -> None:
    """query() returns empty list when log file doesn't exist."""
    t = TelemetryCollector(tmp_path)
    # Remove the log file that was created by __init__
    t.log_path.unlink(missing_ok=True)
    events = t.query()
    assert events == []


# ---------------------------------------------------------------------------
# query() — line 64 (skip blank lines)
# ---------------------------------------------------------------------------

def test_query_skips_blank_lines(tmp_path: Path) -> None:
    """query() skips blank lines in the log file."""
    t = TelemetryCollector(tmp_path)
    t.record("action", "Read", "allowed", tokens=5)
    # Append blank lines
    with t.log_path.open("a", encoding="utf-8") as f:
        f.write("\n\n  \n")
    events = t.query()
    assert len(events) == 1
    assert events[0]["action"] == "Read"


# ---------------------------------------------------------------------------
# query() — lines 67-68 (skip invalid JSON)
# ---------------------------------------------------------------------------

def test_query_skips_invalid_json(tmp_path: Path) -> None:
    """query() skips lines with invalid JSON."""
    t = TelemetryCollector(tmp_path)
    t.record("action", "Read", "allowed", tokens=5)
    # Append invalid JSON
    with t.log_path.open("a", encoding="utf-8") as f:
        f.write("not valid json\n")
    events = t.query()
    assert len(events) == 1
    assert events[0]["action"] == "Read"


# ---------------------------------------------------------------------------
# query() — line 70 (skip when event_type doesn't match)
# ---------------------------------------------------------------------------

def test_query_filters_by_event_type(tmp_path: Path) -> None:
    """query() filters events by event_type."""
    t = TelemetryCollector(tmp_path)
    t.record("action", "Read", "allowed", tokens=5)
    t.record("budget", "Spend", "blocked", tokens=10)
    events = t.query(event_type="budget")
    assert len(events) == 1
    assert events[0]["type"] == "budget"
    assert events[0]["action"] == "Spend"


# ---------------------------------------------------------------------------
# summary() — line 87 (skip blank lines)
# ---------------------------------------------------------------------------

def test_summary_skips_blank_lines(tmp_path: Path) -> None:
    """summary() skips blank lines in the log file."""
    t = TelemetryCollector(tmp_path)
    t.record("action", "Read", "allowed", tokens=5)
    with t.log_path.open("a", encoding="utf-8") as f:
        f.write("\n\n  \n")
    summary = t.summary()
    assert summary["total_events"] == 1
    assert summary["total_tokens"] == 5


# ---------------------------------------------------------------------------
# summary() — lines 90-91 (skip invalid JSON)
# ---------------------------------------------------------------------------

def test_summary_skips_invalid_json(tmp_path: Path) -> None:
    """summary() skips lines with invalid JSON."""
    t = TelemetryCollector(tmp_path)
    t.record("action", "Read", "allowed", tokens=5)
    with t.log_path.open("a", encoding="utf-8") as f:
        f.write("not valid json\n")
    summary = t.summary()
    assert summary["total_events"] == 1
    assert summary["total_tokens"] == 5


# ---------------------------------------------------------------------------
# summary() — no log file returns empty stats
# ---------------------------------------------------------------------------

def test_summary_no_log_file(tmp_path: Path) -> None:
    """summary() returns zero stats when log file doesn't exist."""
    t = TelemetryCollector(tmp_path)
    t.log_path.unlink(missing_ok=True)
    summary = t.summary()
    assert summary["total_events"] == 0
    assert summary["total_tokens"] == 0
    assert summary["total_cost"] == 0.0


# ---------------------------------------------------------------------------
# system_metrics() — lines 111-112 (exception path when psutil fails)
# ---------------------------------------------------------------------------

def test_system_metrics_exception_returns_zeros() -> None:
    """system_metrics() returns zeros when psutil import fails."""
    with patch("builtins.__import__", side_effect=ImportError("no psutil")):
        metrics = system_metrics()
    assert metrics["cpu_percent"] == 0.0
    assert metrics["memory_percent"] == 0.0
    assert metrics["memory_used_mb"] == 0
    assert metrics["memory_total_mb"] == 0


def test_system_metrics_psutil_exception_returns_zeros() -> None:
    """system_metrics() returns zeros when psutil raises during usage."""
    import sys
    from unittest.mock import MagicMock

    # Track if psutil was originally in sys.modules to clean up properly
    _psutil_was_present = "psutil" in sys.modules
    if not _psutil_was_present:
        sys.modules["psutil"] = MagicMock()

    # Save and remove psutil if loaded
    original_psutil = sys.modules.get("psutil")
    mock_psutil = MagicMock()
    mock_psutil.virtual_memory.side_effect = RuntimeError("access denied")
    sys.modules["psutil"] = mock_psutil
    try:
        metrics = system_metrics()
    finally:
        if original_psutil is not None:
            sys.modules["psutil"] = original_psutil
        else:  # pragma: no cover
            sys.modules.pop("psutil", None)
    # Clean up: if psutil wasn't originally present, remove the leaked mock
    if not _psutil_was_present:
        sys.modules.pop("psutil", None)
    assert metrics["cpu_percent"] == 0.0
    assert metrics["memory_percent"] == 0.0
