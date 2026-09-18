"""Tests for runtime/tracing_otel.py — optional OTLP trace export."""

from __future__ import annotations

import sys
import types
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from runtime import tracing_otel


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.delenv("AIZEE_OTEL_ENDPOINT", raising=False)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    # reset warn-once flag
    tracing_otel._warned = False
    yield
    tracing_otel._warned = False


class TestEndpoint:
    def test_none_when_unset(self):
        assert tracing_otel._otel_endpoint() is None

    def test_aizee_var(self, monkeypatch):
        monkeypatch.setenv("AIZEE_OTEL_ENDPOINT", "http://a:4318")
        assert tracing_otel._otel_endpoint() == "http://a:4318"

    def test_standard_var(self, monkeypatch):
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://b:4318")
        assert tracing_otel._otel_endpoint() == "http://b:4318"

    def test_aizee_wins(self, monkeypatch):
        monkeypatch.setenv("AIZEE_OTEL_ENDPOINT", "http://a")
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://b")
        assert tracing_otel._otel_endpoint() == "http://a"


class TestGetTracer:
    def test_none_without_endpoint(self):
        assert tracing_otel.get_tracer() is None

    def test_none_without_sdk(self, monkeypatch, capsys):
        monkeypatch.setenv("AIZEE_OTEL_ENDPOINT", "http://x")
        assert tracing_otel.get_tracer() is None
        assert "not installed" in capsys.readouterr().out

    def test_warn_once(self, monkeypatch, capsys):
        monkeypatch.setenv("AIZEE_OTEL_ENDPOINT", "http://x")
        tracing_otel.get_tracer()
        tracing_otel.get_tracer()
        assert capsys.readouterr().out.count("WARNING") == 1

    def test_tracer_with_fake_sdk(self, monkeypatch):
        monkeypatch.setenv("AIZEE_OTEL_ENDPOINT", "http://x")
        trace_mod: Any = types.ModuleType("opentelemetry.trace")
        provider = MagicMock()
        trace_mod.set_tracer_provider = MagicMock()
        trace_mod.get_tracer = MagicMock(return_value="TRACER")

        otel: Any = types.ModuleType("opentelemetry")
        otel.trace = trace_mod
        exporter: Any = types.ModuleType(
            "opentelemetry.exporter.otlp.proto.http.trace_exporter")
        exporter.OTLPSpanExporter = MagicMock()
        resources: Any = types.ModuleType("opentelemetry.sdk.resources")
        resources.Resource = MagicMock()
        sdk_trace: Any = types.ModuleType("opentelemetry.sdk.trace")
        sdk_trace.TracerProvider = MagicMock(return_value=provider)
        sdk_export: Any = types.ModuleType("opentelemetry.sdk.trace.export")
        sdk_export.BatchSpanProcessor = MagicMock()

        modules = {
            "opentelemetry": otel,
            "opentelemetry.trace": trace_mod,
            "opentelemetry.exporter.otlp.proto.http.trace_exporter": exporter,
            "opentelemetry.sdk.resources": resources,
            "opentelemetry.sdk.trace": sdk_trace,
            "opentelemetry.sdk.trace.export": sdk_export,
        }
        with patch.dict(sys.modules, modules):
            assert tracing_otel.get_tracer("svc") == "TRACER"
            sdk_trace.TracerProvider.assert_called_once()
            trace_mod.get_tracer.assert_called_with("svc")


class TestRecordSpan:
    def test_noop_without_endpoint(self):
        tracing_otel.record_span("s")  # silent no-op

    def test_noop_without_sdk(self, monkeypatch, capsys):
        monkeypatch.setenv("AIZEE_OTEL_ENDPOINT", "http://x")
        tracing_otel.record_span("s")
        assert "WARNING" in capsys.readouterr().out

    def test_span_with_fake_sdk(self, monkeypatch):
        monkeypatch.setenv("AIZEE_OTEL_ENDPOINT", "http://x")
        span = MagicMock()
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=span)
        ctx.__exit__ = MagicMock(return_value=False)
        tracer = MagicMock()
        tracer.start_as_current_span = MagicMock(return_value=ctx)

        trace_mod: Any = types.ModuleType("opentelemetry.trace")
        trace_mod.get_tracer = MagicMock(return_value=tracer)
        otel: Any = types.ModuleType("opentelemetry")
        otel.trace = trace_mod

        with patch.dict(sys.modules, {
                "opentelemetry": otel, "opentelemetry.trace": trace_mod}):
            tracing_otel.record_span(
                "op", {"k": "v", "n": 1}, duration_s=0.5)
            tracer.start_as_current_span.assert_called_once()
            assert span.set_attribute.call_count == 2


class TestHelpers:
    def test_ns(self):
        assert tracing_otel._ns(1.5) == 1_500_000_000
        assert tracing_otel._ns(0) == 0

    @pytest.mark.parametrize("v,expected", [
        ("s", "s"), (True, True), (3, 3), (1.5, 1.5),
        ([], ""), (["a", "b"], ["a", "b"]), ([1, 2], [1, 2]),
        ([{"k": 1}], "[{'k': 1}]"), ({"a": 1}, "{'a': 1}"),
        (("x",), ["x"]),
    ])
    def test_coerce(self, v, expected):
        assert tracing_otel._coerce(v) == expected
