"""Tests for runtime/otel_exporter.py — OpenTelemetry exporter."""

from __future__ import annotations

import json
import time
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

from runtime.otel_exporter import (
    OTelConfig,
    OTelExporter,
    OTelSpan,
)


class TestOTelConfig:
    """Tests for OTelConfig."""

    def test_defaults(self) -> None:
        c = OTelConfig()
        assert c.service_name == "ai-global-os"
        assert c.batch_size == 50
        assert c.endpoint == ""

    def test_custom(self) -> None:
        c = OTelConfig(endpoint="http://localhost:4318", service_name="test")
        assert c.endpoint == "http://localhost:4318"
        assert c.service_name == "test"


class TestOTelExporter:
    """Tests for OTelExporter."""

    def test_export_span_no_endpoint_no_fallback(self) -> None:
        """Exporting without endpoint or fallback should not fail."""
        exporter = OTelExporter(OTelConfig())
        exporter.export_span({
            "trace_id": "abc",
            "span_id": "def",
            "name": "test",
            "start_time": time.time(),
            "end_time": time.time(),
        })
        # Should not raise, buffer should have the span
        assert len(exporter._buffer) >= 1

    def test_export_span_with_fallback(self, tmp_path: Path) -> None:
        fallback = tmp_path / "traces.jsonl"
        exporter = OTelExporter(OTelConfig(fallback_file=fallback, batch_size=1))
        exporter.export_span({
            "trace_id": "abc",
            "span_id": "def",
            "name": "test",
            "start_time": time.time(),
            "end_time": time.time(),
            "attributes": {"action": "Bash"},
        })
        # batch_size=1 triggers immediate flush
        assert fallback.exists()
        content = fallback.read_text(encoding="utf-8").strip()
        assert len(content) > 0
        entry = json.loads(content.split("\n")[0])
        assert "name" in entry

    def test_flush_empty_buffer(self) -> None:
        exporter = OTelExporter(OTelConfig())
        assert exporter.flush() is True

    def test_flush_with_fallback(self, tmp_path: Path) -> None:
        fallback = tmp_path / "traces.jsonl"
        exporter = OTelExporter(OTelConfig(fallback_file=fallback, batch_size=100))
        for i in range(3):
            exporter.export_span({
                "trace_id": f"trace_{i}",
                "span_id": f"span_{i}",
                "name": f"test_{i}",
                "start_time": time.time(),
                "end_time": time.time(),
            })
        exporter.flush()
        lines = [line for line in fallback.read_text(encoding="utf-8").strip().split("\n") if line]
        assert len(lines) == 3

    def test_resource_attributes(self) -> None:
        exporter = OTelExporter(OTelConfig(service_name="test-svc", service_version="2.0"))
        attrs = exporter._resource_attributes()
        assert any(a["key"] == "service.name" and a["value"]["stringValue"] == "test-svc" for a in attrs)
        assert any(a["key"] == "service.version" and a["value"]["stringValue"] == "2.0" for a in attrs)

    def test_span_to_otlp_format(self) -> None:
        exporter = OTelExporter(OTelConfig())
        span = {
            "trace_id": "abc123",
            "span_id": "def456",
            "name": "act.Bash",
            "start_time": 1700000000.0,
            "end_time": 1700000001.0,
            "attributes": {"action": "Bash", "tokens": 100, "success": True},
        }
        otlp_span = exporter._span_to_otlp(span)
        assert otlp_span["traceId"] == "abc123"
        assert otlp_span["spanId"] == "def456"
        assert otlp_span["name"] == "act.Bash"
        assert otlp_span["kind"] == "SPAN_KIND_INTERNAL"
        assert len(otlp_span["attributes"]) == 3
        # Check attribute types
        attr_map = {a["key"]: a["value"] for a in otlp_span["attributes"]}
        assert "stringValue" in attr_map["action"]
        assert "intValue" in attr_map["tokens"]
        assert "boolValue" in attr_map["success"]

    def test_span_to_otlp_with_error(self) -> None:
        exporter = OTelExporter(OTelConfig())
        span = {
            "trace_id": "abc",
            "span_id": "def",
            "name": "failed",
            "start_time": 0,
            "end_time": 1,
            "error": "Something went wrong",
        }
        otlp_span = exporter._span_to_otlp(span)
        assert otlp_span["status"]["code"] == "STATUS_CODE_ERROR"
        assert "Something went wrong" in otlp_span["status"]["message"]

    def test_build_otlp_request(self) -> None:
        exporter = OTelExporter(OTelConfig(service_name="test"))
        spans = [
            {"trace_id": "t1", "span_id": "s1", "name": "span1", "start_time": 0, "end_time": 1},
            {"trace_id": "t1", "span_id": "s2", "name": "span2", "start_time": 1, "end_time": 2},
        ]
        request = exporter._build_otlp_request(spans)
        assert "resourceSpans" in request
        assert len(request["resourceSpans"]) == 1
        assert len(request["resourceSpans"][0]["scopeSpans"][0]["spans"]) == 2

    def test_batch_triggers_flush(self, tmp_path: Path) -> None:
        fallback = tmp_path / "traces.jsonl"
        exporter = OTelExporter(OTelConfig(fallback_file=fallback, batch_size=3))
        for i in range(3):
            exporter.export_span({
                "trace_id": f"t{i}",
                "span_id": f"s{i}",
                "name": f"span{i}",
                "start_time": 0,
                "end_time": 1,
            })
        # batch_size=3 should trigger flush
        assert fallback.exists()
        lines = [line for line in fallback.read_text(encoding="utf-8").strip().split("\n") if line]
        assert len(lines) == 3

    def test_send_http_success(self) -> None:
        exporter = OTelExporter(OTelConfig(endpoint="http://localhost:4318/v1/traces"))
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = exporter._send_http(b'{"test": true}')
        assert result is True

    def test_send_http_failure(self) -> None:
        exporter = OTelExporter(OTelConfig(endpoint="http://localhost:9999"))
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("fail")):
            result = exporter._send_http(b'{"test": true}')
        assert result is False

    def test_shutdown_flushes(self, tmp_path: Path) -> None:
        fallback = tmp_path / "traces.jsonl"
        exporter = OTelExporter(OTelConfig(fallback_file=fallback, batch_size=100))
        exporter.export_span({
            "trace_id": "t1",
            "span_id": "s1",
            "name": "span1",
            "start_time": 0,
            "end_time": 1,
        })
        exporter.shutdown()
        assert fallback.exists()


class TestOTelSpan:
    """Tests for OTelSpan context manager."""

    def test_span_context_manager(self) -> None:
        exporter = OTelExporter(OTelConfig())
        with OTelSpan(exporter, "test.span", trace_id="trace1") as span:
            span.set_attribute("key", "value")
        # Span should be in buffer
        assert len(exporter._buffer) >= 1
        span_data = exporter._buffer[-1]
        assert span_data["name"] == "test.span"
        assert span_data["trace_id"] == "trace1"
        assert span_data["attributes"]["key"] == "value"

    def test_span_with_exception(self) -> None:
        exporter = OTelExporter(OTelConfig())
        try:
            with OTelSpan(exporter, "test.span"):
                raise ValueError("test error")
        except ValueError:
            pass  # expected
        span_data = exporter._buffer[-1]
        assert "error" in span_data
        assert "test error" in span_data["error"]

    def test_span_generates_span_id(self) -> None:
        exporter = OTelExporter(OTelConfig())
        with OTelSpan(exporter, "test") as span:
            assert len(span._span_id) == 16
