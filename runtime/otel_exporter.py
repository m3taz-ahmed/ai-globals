#!/usr/bin/env python3
"""OpenTelemetry-compatible trace exporter for AI Global OS.

Exports agent traces in OTLP (OpenTelemetry Protocol) JSON format,
compatible with any OTel collector (Jaeger, Tempo, Honeycomb, etc.).

Does NOT require the ``opentelemetry`` package — produces OTLP-compliant
JSON that can be sent via HTTP to any OTLP/HTTP endpoint.

Features:
- Span export with trace context
- Resource attributes (service name, version)
- Batch export with configurable flush interval
- Local file fallback (write to JSONL if no endpoint configured)
- Integration with the existing ``TracerProvider``

Usage::

    from runtime.otel_exporter import OTelExporter
    exporter = OTelExporter(
        endpoint="http://localhost:4318/v1/traces",
        service_name="ai-global-os",
    )
    exporter.export_span({
        "trace_id": "abc123",
        "span_id": "def456",
        "name": "act.Bash",
        "start_time": 1700000000,
        "end_time": 1700000001,
        "attributes": {"action": "Bash", "decision": "allow"},
    })
"""

from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class OTelConfig:
    """Configuration for the OTel exporter."""

    endpoint: str = ""  # OTLP/HTTP endpoint (e.g., http://localhost:4318/v1/traces)
    service_name: str = "ai-global-os"
    service_version: str = "1.0.0"
    environment: str = "development"
    batch_size: int = 50
    flush_interval_seconds: float = 5.0
    fallback_file: Path | None = None  # Write to file if no endpoint
    headers: dict[str, str] = field(default_factory=dict)


class OTelExporter:
    """OpenTelemetry-compatible trace exporter.

    Exports spans in OTLP/JSON format. If no endpoint is configured,
    spans are written to a local JSONL file as fallback.
    """

    def __init__(self, config: OTelConfig | None = None) -> None:
        self.config = config or OTelConfig()
        self._buffer: list[dict[str, Any]] = []
        self._lock = threading.Lock()
        self._last_flush = time.time()

    def _resource_attributes(self) -> list[dict[str, Any]]:
        """Build OTel resource attributes."""
        return [
            {"key": "service.name", "value": {"stringValue": self.config.service_name}},
            {"key": "service.version", "value": {"stringValue": self.config.service_version}},
            {"key": "deployment.environment", "value": {"stringValue": self.config.environment}},
        ]

    def _span_to_otlp(self, span: dict[str, Any]) -> dict[str, Any]:
        """Convert a span dict to OTLP format."""
        attributes = []
        for key, value in span.get("attributes", {}).items():
            if isinstance(value, str):
                attr_value: dict[str, Any] = {"stringValue": value}
            elif isinstance(value, bool):
                attr_value = {"boolValue": value}
            elif isinstance(value, int):
                attr_value = {"intValue": str(value)}
            elif isinstance(value, float):
                attr_value = {"doubleValue": value}
            else:
                attr_value = {"stringValue": str(value)}
            attributes.append({"key": key, "value": attr_value})

        # Status
        status: dict[str, Any] = {"code": "STATUS_CODE_OK"}
        if span.get("error"):
            status = {"code": "STATUS_CODE_ERROR", "message": str(span["error"])}

        return {
            "traceId": span.get("trace_id", ""),
            "spanId": span.get("span_id", ""),
            "parentSpanId": span.get("parent_span_id", ""),
            "name": span.get("name", "unnamed"),
            "kind": "SPAN_KIND_INTERNAL",
            "startTimeUnixNano": str(int(span.get("start_time", 0) * 1_000_000_000)),
            "endTimeUnixNano": str(int(span.get("end_time", 0) * 1_000_000_000)),
            "attributes": attributes,
            "status": status,
        }

    def _build_otlp_request(self, spans: list[dict[str, Any]]) -> dict[str, Any]:
        """Build an OTLP export request."""
        return {
            "resourceSpans": [
                {
                    "resource": {"attributes": self._resource_attributes()},
                    "scopeSpans": [
                        {
                            "scope": {"name": "ai-global-os", "version": self.config.service_version},
                            "spans": [self._span_to_otlp(s) for s in spans],
                        }
                    ],
                }
            ]
        }

    def export_span(self, span: dict[str, Any]) -> None:
        """Export a single span (buffered)."""
        with self._lock:
            self._buffer.append(span)
            should_flush = (
                len(self._buffer) >= self.config.batch_size
                or (time.time() - self._last_flush) >= self.config.flush_interval_seconds
            )
        if should_flush:
            self.flush()

    def flush(self) -> bool:
        """Flush buffered spans to the endpoint or fallback file."""
        with self._lock:
            if not self._buffer:
                return True
            spans = self._buffer[:]
            self._buffer.clear()
            self._last_flush = time.time()

        otlp_request = self._build_otlp_request(spans)
        payload = json.dumps(otlp_request).encode("utf-8")

        if self.config.endpoint:
            return self._send_http(payload)
        if self.config.fallback_file:
            return self._write_fallback(spans)
        return True  # No endpoint or fallback — silently drop

    def _send_http(self, payload: bytes) -> bool:
        """Send OTLP JSON via HTTP POST."""
        try:
            headers = {
                "Content-Type": "application/json",
                **self.config.headers,
            }
            req = urllib.request.Request(
                self.config.endpoint,
                data=payload,
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                ok: bool = resp.status == 200
                return ok
        except (urllib.error.URLError, OSError, TimeoutError):
            # Network error — try fallback file
            if self.config.fallback_file:
                return self._write_fallback(json.loads(payload.decode("utf-8")).get("resourceSpans", []))
            return False

    def _write_fallback(self, spans: list[Any]) -> bool:
        """Write spans to a local JSONL file as fallback."""
        if not self.config.fallback_file:
            return False
        try:
            self.config.fallback_file.parent.mkdir(parents=True, exist_ok=True)
            with self.config.fallback_file.open("a", encoding="utf-8") as f:
                for span in spans:
                    if (isinstance(span, dict) and "traceId" in span) or isinstance(span, dict):
                        f.write(json.dumps(span) + "\n")
            return True
        except OSError:
            return False

    def shutdown(self) -> None:
        """Flush remaining spans and shutdown."""
        self.flush()


class OTelSpan:
    """Context manager for creating and exporting a span."""

    def __init__(
        self,
        exporter: OTelExporter,
        name: str,
        trace_id: str = "",
        parent_span_id: str = "",
        attributes: dict[str, Any] | None = None,
    ) -> None:
        self.exporter = exporter
        self.name = name
        self.trace_id = trace_id
        self.parent_span_id = parent_span_id
        self.attributes = attributes or {}
        self._start_time: float = 0.0
        self._span_id: str = ""

    def __enter__(self) -> OTelSpan:
        import uuid
        self._start_time = time.time()
        self._span_id = uuid.uuid4().hex[:16]
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        end_time = time.time()
        span_data = {
            "trace_id": self.trace_id,
            "span_id": self._span_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "start_time": self._start_time,
            "end_time": end_time,
            "attributes": self.attributes,
        }
        if exc_type:
            span_data["error"] = str(exc_val)
        self.exporter.export_span(span_data)

    def set_attribute(self, key: str, value: Any) -> None:
        """Set a span attribute."""
        self.attributes[key] = value


if __name__ == "__main__":
    # Demo: export a span to a local file
    config = OTelConfig(fallback_file=Path("state/otel_traces.jsonl"))
    exporter = OTelExporter(config)
    with OTelSpan(exporter, "demo.span", attributes={"test": True}) as span:
        span.set_attribute("result", "success")
    exporter.shutdown()
    print("Span exported to state/otel_traces.jsonl")
