#!/usr/bin/env python3
"""Tests for runtime.metrics."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from runtime.metrics import (
    CollectorRegistry,
    Counter,
    ExceptionCounter,
    Gauge,
    Histogram,
    Info,
    LabelValueError,
    MetricDuplicationError,
    MetricNameError,
    Summary,
    Timer,
    _base_name,
    _format_labels,
    format_metrics,
    generate_latest,
    inprogress,
    register,
    unregister,
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


# --- Label validation ---

def test_invalid_label_name():
    with pytest.raises(MetricNameError):
        Counter("x", "d", labels=("__name__",))


def test_invalid_label_name_format():
    with pytest.raises(MetricNameError):
        Counter("x", "d", labels=("123bad",))


# --- labels() with no labels but kwargs ---

def test_labels_with_kwargs_on_labelless_metric():
    c = Counter("x", "A counter")
    with pytest.raises(LabelValueError):
        c.labels(foo="bar")


# --- Summary quantile with no observations ---

def test_summary_quantile_empty():
    s = Summary("empty_latency", "Empty latency")
    s.labels()  # create default child with empty deque
    samples = {sm.name: sm.value for sm in s.collect()}
    # quantile of empty returns 0.0
    assert samples["empty_latency"] == 0.0


# --- Registry duplicate and unregister ---

def test_registry_duplicate():
    registry = CollectorRegistry()
    c = Counter("dup", "A counter")
    registry.register(c)
    with pytest.raises(MetricDuplicationError):
        registry.register(Counter("dup", "Another"))


def test_registry_unregister():
    registry = CollectorRegistry()
    c = Counter("temp", "A counter")
    registry.register(c)
    assert "temp" in registry.names()
    registry.unregister(c)
    assert "temp" not in registry.names()


# --- RestrictedRegistry ---

def test_restricted_registry():
    registry = CollectorRegistry()
    c = Counter("a_total", "A counter")
    g = Gauge("b", "A gauge")
    c.inc(5)
    g.set(3)
    registry.register(c)
    registry.register(g)
    restricted = registry.restricted_registry(["a_total"])
    samples = restricted.collect()
    names = {s.name for s in samples}
    assert "a_total_total" in names
    assert "b" not in names


# --- Global register/unregister functions ---

def test_global_register_unregister():
    c = Counter("global_counter", "A global counter")
    register(c)
    # Should be in global registry
    output = generate_latest()
    assert "global_counter" in output
    unregister(c)
    output2 = generate_latest()
    assert "global_counter" not in output2


# --- _base_name ---

def test_base_name_total():
    assert _base_name("foo_total") == "foo"


def test_base_name_sum():
    assert _base_name("foo_sum") == "foo"


def test_base_name_count():
    assert _base_name("foo_count") == "foo"


def test_base_name_bucket():
    assert _base_name("foo_bucket") == "foo"


def test_base_name_no_suffix():
    assert _base_name("foo") == "foo"


# --- _format_labels ---

def test_format_labels_empty():
    assert _format_labels({}) == ""


def test_format_labels_non_empty():
    result = _format_labels({"method": "GET"})
    assert result == '{method="GET"}'


# --- ExceptionCounter ---

def test_exception_counter_no_exception():
    c = ExceptionCounter("errors_total", "Total errors")
    c.labels()  # ensure child exists
    with c:
        pass  # no exception
    assert c.collect()[0].value == 0.0


def test_exception_counter_with_exception():
    c = ExceptionCounter("errors2_total", "Total errors")
    try:
        with c:
            raise ValueError("boom")
    except ValueError:
        pass
    assert c.collect()[0].value == 1.0


# --- inprogress ---

def test_inprogress_context_manager():
    g = Gauge("inflight", "In-flight operations")
    with inprogress(g):
        assert g.collect()[0].value == 1.0
    assert g.collect()[0].value == 0.0


# --- format_metrics ---

def test_format_metrics():
    mock_budget = MagicMock()
    mock_budget.usage = {
        "global": {"tokens": 500, "calls": 10},
        "session": {"tokens": 200, "calls": 5},
    }
    mock_kernel = MagicMock()
    mock_kernel.status.return_value = {
        "workflows": ["w1", "w2"],
        "rules": ["r1"],
        "budgets": ["b1"],
    }
    mock_kernel.budget = mock_budget
    output = format_metrics(mock_kernel)
    assert "aizee_workflows_total 2" in output
    assert "aizee_rules_total 1" in output
    assert "aizee_budgets_total 1" in output
    assert 'scope="global"' in output
    assert "aizee_budget_tokens_total" in output
    assert "aizee_budget_calls_total" in output
    assert 'scope="session"' in output
