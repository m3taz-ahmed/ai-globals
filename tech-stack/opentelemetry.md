[TECH] OpenTelemetry
[OBJ] Vendor-neutral observability framework for generating, collecting, and exporting telemetry data (traces, metrics, logs) via the OTLP protocol.
[RULES]
1. [REQ] Instrument applications using OpenTelemetry SDKs (auto-instrumentation or manual) for traces, metrics, and logs; emit telemetry via OTLP (gRPC or HTTP) to a Collector.
2. [REQ] Deploy the OpenTelemetry Collector as an agent (DaemonSet/sidecar) and/or gateway (deployment) pipeline; configure receivers, processors, and exporters in `otel-collector-config.yaml`.
3. [REQ] Use semantic conventions for resource attributes (service.name, service.version, deployment.environment, host.name) to ensure consistent correlation across signals.
4. [REQ] Propagate trace context (W3C TraceContext `traceparent` header) across service boundaries; use baggage for cross-cutting business context (tenant ID, user ID).
5. [REQ] Use span attributes (not span events) for structured queryable data; use span events for timestamped log-like annotations within a span.
6. [REQ] Configure batch exporting (batch processor) with `send_batch_size`, `timeout`, and `max_export_batch_size` to balance throughput and latency.
7. [REQ] Use tail-based sampling in the Collector (groupbytrace processor or sampling processors) for intelligent sampling that preserves error and slow traces.
8. [REQ] Export metrics using the OTLP metrics exporter with cumulative or delta temporality matching the backend (Prometheus prefers cumulative, some backends prefer delta).
9. [REQ] Enable logs via OTLP logs pipeline; correlate logs with traces by injecting `trace_id` and `span_id` into log records using the Logs Data Model.
10. [CMD] Use `otelcol` (Collector distribution) with `--config` flag; validate config with `otelcol validate --config otel-collector-config.yaml`.
11. [CMD] Use `opentelemetry-instrument` (Python) or `otel-agent-inject` (Java/K8s) for zero-code auto-instrumentation of common libraries.
12. [CMD] Use the Collector's `health_check` extension on port 13133 for liveness probes in Kubernetes.
13. [PROHIBIT] Never use head-based sampling in production for traces if you need error/slow-trace visibility — use tail-based sampling in the Collector instead.
14. [PROHIBIT] Never send telemetry directly from applications to the backend without a Collector — the Collector provides buffering, retry, enrichment, and protocol translation.
15. [PROHIBIT] Never store sensitive PII in span attributes, baggage, or log payloads — use attribute redaction processors to strip known sensitive fields.
[COMPAT]
- v1.25.x (Collector): OTLP 1.3 spec, stable metrics SDK, logs pipeline GA
- v1.30.x (Collector): Prometheus receiver improvements, `confmap` for env var interpolation
- OTLP v1.3.0: Stable protocol for traces, metrics, and logs over gRPC/HTTP
[REFS]
- https://opentelemetry.io/docs/
- https://opentelemetry.io/docs/collector/
- https://opentelemetry.io/docs/specs/otel/
- https://opentelemetry.io/docs/specs/otlp/
