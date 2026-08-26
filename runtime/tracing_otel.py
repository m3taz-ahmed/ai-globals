"""Optional OpenTelemetry (OTLP) trace export for aiZee.

This module is strictly additive: it never replaces the existing JSONL span
export path. It exposes a safe, always-callable API so callers can emit spans
to an OTLP collector when one is configured, and otherwise become a no-op.

Configuration (any one enables OTLP export):
    - OTEL_EXPORTER_OTLP_ENDPOINT  (standard OpenTelemetry env var)
    - AIZEE_OTEL_ENDPOINT          (aiZee-specific override)

The OpenTelemetry SDK is an OPTIONAL dependency. When it is not installed the
module logs a single warning and all functions degrade to no-ops; it never
raises because of a missing package.
"""

from __future__ import annotations

import os
import threading
import time
from typing import Any


def _otel_endpoint() -> str | None:
    """Return the configured OTLP endpoint, or None if tracing is disabled."""
    return os.environ.get("AIZEE_OTEL_ENDPOINT") or os.environ.get(
        "OTEL_EXPORTER_OTLP_ENDPOINT"
    )


def get_tracer(name: str = "aizee") -> Any | None:
    """Return an OpenTelemetry tracer, or None when OTLP export is disabled.

    A None return means callers should simply skip OTLP export and continue
    using the existing JSONL tracing path unchanged.
    """
    if _otel_endpoint() is None:
        return None

    try:
        from opentelemetry import trace  # type: ignore
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (  # type: ignore
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.resources import Resource  # type: ignore
        from opentelemetry.sdk.trace import TracerProvider  # type: ignore
        from opentelemetry.sdk.trace.export import (  # type: ignore
            BatchSpanProcessor,
        )
    except ImportError:
        _warn_once(
            "OpenTelemetry packages are not installed; OTLP export disabled. "
            "Install opentelemetry-sdk and opentelemetry-exporter-otlp to enable."
        )
        return None

    endpoint = _otel_endpoint()
    provider = TracerProvider(resource=Resource.create({"service.name": name}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    trace.set_tracer_provider(provider)
    return trace.get_tracer(name)


_warned = False
_warn_lock = threading.Lock()


def _warn_once(message: str) -> None:
    global _warned
    with _warn_lock:
        if _warned:
            return
        _warned = True
        print(f"[aizee-tracing-otel] WARNING: {message}")


def record_span(name: str, attributes: dict[str, Any] | None = None, duration_s: float | None = None) -> None:
    """Emit a span over OTLP if enabled; always safe to call.

    This never interacts with the JSONL span path. If OTLP export is disabled
    (no endpoint configured, or the SDK is missing) this is a silent no-op.
    """
    endpoint = _otel_endpoint()
    if endpoint is None:
        return

    try:
        from opentelemetry import trace
    except ImportError:
        _warn_once(
            "OpenTelemetry packages are not installed; OTLP export disabled. "
            "Install opentelemetry-sdk and opentelemetry-exporter-otlp to enable."
        )
        return

    tracer = trace.get_tracer("aizee")
    start = time.time() - (duration_s or 0.0)
    with tracer.start_as_current_span(name, start_time=_ns(start)) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, _coerce(value))


def _ns(seconds: float) -> int:
    """Convert a float epoch timestamp (seconds) to nanoseconds for OTel."""
    return int(seconds * 1_000_000_000)


def _coerce(value: Any) -> Any:
    """Coerce arbitrary attributes to OTel-supported scalar types."""
    if isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, (list, tuple)):
        if not value:
            return ""
        first = value[0]
        if isinstance(first, (str, bool, int, float)):
            return [_coerce(v) for v in value]
        return str(value)
    return str(value)
