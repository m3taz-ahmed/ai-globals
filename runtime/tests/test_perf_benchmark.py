#!/usr/bin/env python3
"""Tests for performance benchmark module."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


class TestPerfBenchmark:
    """Tests for perf_benchmark.py."""

    def test_benchmark_runs_and_returns_zero(self) -> None:
        """Benchmark script runs without error and exits 0."""
        result = subprocess.run(
            [sys.executable, str(ROOT / "runtime" / "perf_benchmark.py"),
             "--iterations", "5", "--json"],
            capture_output=True, text=True, shell=False, timeout=60,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "kernel.act (read)" in data
        assert "persona.detect" in data

    def test_benchmark_json_output_is_valid(self) -> None:
        """JSON output contains expected fields."""
        result = subprocess.run(
            [sys.executable, str(ROOT / "runtime" / "perf_benchmark.py"),
             "--iterations", "3", "--json"],
            capture_output=True, text=True, shell=False, timeout=60,
        )
        data = json.loads(result.stdout)
        for _name, stats in data.items():
            if "error" not in stats:
                assert "mean_ms" in stats
                assert "median_ms" in stats
                assert "iterations" in stats
                assert stats["iterations"] == 3
