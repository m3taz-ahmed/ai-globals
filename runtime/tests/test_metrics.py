#!/usr/bin/env python3
"""Tests for runtime.metrics."""

from __future__ import annotations

import pytest

from runtime.metrics import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    Info,
    MetricNameError,
    Summary,
    Timer,
    generate_latest,
)


def test_counter_increments():
    c = Counter("requests_total", "Total requests")
    c.inc()
    c.inc(2)
    samples = c.collect()
    assert len(samples) == 1
    assert samples[0].name == "requests_total_total"
    assert samples[0].value == 3.0


def test_counter_with_labels():
    c = Counter("requests_total", "Total requests", labels=("method",))
    c.labels(method="GET").inc()
    c.labels(method="POST").inc(2)
    samples = c.collect()
    assert {s.labels["method"]: s.value for s in samples} == {"GET": 1.0, "POST": 2.0}


def test_gauge_set_inc_dec():
    g = Gauge("temperature", "Current temperature")
    g.set(20)
    g.inc(5)
    g.dec(2)
    assert g.collect()[0].value == 23.0


def test_histogram_observe():
    h = Histogram("request_duration_seconds", "Request duration")
    h.observe(0.05)
    h.observe(0.5)
    h.observe(5.0)
    samples = {s.name for s in h.collect()}
    assert "request_duration_seconds_sum" in samples
    assert "request_duration_seconds_count" in samples
    assert "request_duration_seconds_bucket" in samples


def test_summary_observe():
    s = Summary("request_latency", "Request latency")
    for i in range(1, 101):
        s.observe(float(i))
    samples = {s.name for s in s.collect()}
    assert "request_latency_sum" in samples
    assert "request_latency_count" in samples
    assert any(s.name == "request_latency" for s in s.collect())


def test_info():
    i = Info("build", "Build information")
    i.info({"version": "4.22.0", "branch": "main"})
    sample = i.collect()[0]
    assert sample.labels["version"] == "4.22.0"
    assert sample.value == 1.0


def test_registry_collects():
    registry = CollectorRegistry()
    c = Counter("a_total", "A counter")
    g = Gauge("b", "A gauge")
    c.inc(10)
    g.set(5)
    registry.register(c)
    registry.register(g)
    samples = {s.name: s.value for s in registry.collect()}
    assert samples["a_total_total"] == 10.0
    assert samples["b"] == 5.0


def test_generate_latest():
    registry = CollectorRegistry()
    c = Counter("requests_total", "Total requests")
    c.inc(3)
    registry.register(c)
    output = generate_latest(registry)
    assert "# HELP requests_total Total requests" in output
    assert "# TYPE requests_total counter" in output
    assert "requests_total_total 3.0" in output


def test_invalid_metric_name():
    with pytest.raises(MetricNameError):
        Counter("123-invalid", "Bad name")


def test_timer():
    s = Summary("op_latency", "Operation latency")
    with Timer(s):
        pass
    samples = {s.name: s.value for s in s.collect()}
    assert "op_latency_count" in samples
    assert samples["op_latency_count"] == 1.0
