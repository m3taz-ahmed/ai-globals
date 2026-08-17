#!/usr/bin/env python3
"""Performance benchmarks for aiZee core operations.

Measures latency of:
  - Kernel.act (policy gate)
  - PersonaDetector.detect
  - MemoryStore.search_hybrid
  - SkillResolver.list_skills

Usage:
  python runtime/perf_benchmark.py
  python runtime/perf_benchmark.py --iterations 1000
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any

# Ensure root is on path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _benchmark(func: Any, iterations: int, *args: Any, **kwargs: Any) -> dict[str, float]:
    """Run func iterations times and return timing stats in milliseconds."""
    latencies: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        func(*args, **kwargs)
        end = time.perf_counter()
        latencies.append((end - start) * 1000)

    return {
        "iterations": iterations,
        "mean_ms": round(statistics.mean(latencies), 3),
        "median_ms": round(statistics.median(latencies), 3),
        "p95_ms": round(statistics.quantiles(latencies, n=20)[18], 3) if len(latencies) >= 20 else 0.0,
        "p99_ms": round(statistics.quantiles(latencies, n=100)[98], 3) if len(latencies) >= 100 else 0.0,
        "min_ms": round(min(latencies), 3),
        "max_ms": round(max(latencies), 3),
        "stdev_ms": round(statistics.stdev(latencies), 3) if len(latencies) > 1 else 0.0,
    }


def bench_kernel_act(iterations: int) -> dict[str, Any]:
    """Benchmark Kernel.act (policy gate for a read action)."""
    from runtime.kernel import Kernel

    k = Kernel(ROOT, ROOT)
    return _benchmark(lambda: k.act("read", tokens=10), iterations)


def bench_persona_detect(iterations: int) -> dict[str, Any]:
    """Benchmark PersonaDetector.detect."""
    from runtime.persona import PersonaDetector

    detector = PersonaDetector()
    text = "build a secure docker API with postgres and redis caching"
    return _benchmark(lambda: detector.detect(text), iterations)


def bench_skill_list(iterations: int) -> dict[str, Any]:
    """Benchmark SkillResolver.list_skills."""
    from runtime.skill_resolver import SkillResolver

    resolver = SkillResolver(ROOT, ROOT)
    return _benchmark(lambda: resolver.list_skills(), iterations)


def bench_memory_search(iterations: int) -> dict[str, Any]:
    """Benchmark MemoryStore.search_hybrid."""
    from memory.store import MemoryStore

    store = MemoryStore(ROOT)
    return _benchmark(lambda: store.search("docker", limit=5), iterations)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="aiZee performance benchmarks")
    parser.add_argument("--iterations", type=int, default=100, help="Iterations per benchmark")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args(argv)

    benchmarks = {
        "kernel.act (read)": bench_kernel_act,
        "persona.detect": bench_persona_detect,
        "skill.list": bench_skill_list,
    }

    # Memory search only if store exists
    if (ROOT / "memory" / "store.db").exists():
        benchmarks["memory.search"] = bench_memory_search

    results = {}
    for name, func in benchmarks.items():
        try:
            results[name] = func(args.iterations)
        except Exception as e:
            results[name] = {"error": str(e)}

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(f"\naiZee Performance Benchmarks ({args.iterations} iterations)\n")
        print(f"{'Benchmark':<30} {'Mean (ms)':>10} {'Median (ms)':>12} {'P95 (ms)':>10} {'P99 (ms)':>10}")
        print("-" * 75)
        for name, stats in results.items():
            if "error" in stats:
                print(f"{name:<30} {'ERROR':>10} {stats['error']}")
            else:
                print(
                    f"{name:<30} {stats['mean_ms']:>10.3f} {stats['median_ms']:>12.3f} "
                    f"{stats['p95_ms']:>10.3f} {stats['p99_ms']:>10.3f}"
                )
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
