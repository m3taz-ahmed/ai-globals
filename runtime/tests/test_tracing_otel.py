"""Tests for the optional OpenTelemetry (OTLP) trace export module.

These tests verify the no-op / disabled behavior without requiring the
opentelemetry-sdk package to be installed. When OTLP is not configured, all
functions must degrade to safe no-ops and never raise.
"""

from __future__ import annotations

import pytest

from runtime.tracing_otel import _otel_endpoint, get_tracer, record_span


@pytest.fixture
def no_otel_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove all OTLP endpoint env vars so tracing is disabled."""
    for var in ("AIZEE_OTEL_ENDPOINT", "OTEL_EXPORTER_OTLP_ENDPOINT"):
        monkeypatch.delenv(var, raising=False)


def test_endpoint_none_when_unconfigured(no_otel_env: None) -> None:
    assert _otel_endpoint() is None


def test_endpoint_from_aizee_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AIZEE_OTEL_ENDPOINT", "http://localhost:4318")
    assert _otel_endpoint() == "http://localhost:4318"


def test_endpoint_from_otel_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AIZEE_OTEL_ENDPOINT", raising=False)
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector:4318")
    assert _otel_endpoint() == "http://collector:4318"


def test_aizee_var_takes_precedence(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AIZEE_OTEL_ENDPOINT", "http://aizee:4318")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel:4318")
    assert _otel_endpoint() == "http://aizee:4318"


def test_get_tracer_none_when_disabled(no_otel_env: None) -> None:
    assert get_tracer() is None


def test_record_span_noop_when_disabled(no_otel_env: None) -> None:
    # Must not raise even with arbitrary attributes.
    record_span("test-span", {"key": "value"}, duration_s=0.5)


def test_record_span_noop_with_no_args(no_otel_env: None) -> None:
    record_span("bare-span")


def test_get_tracer_custom_name(no_otel_env: None) -> None:
    # Still None when disabled, regardless of name.
    assert get_tracer("custom-service") is None
