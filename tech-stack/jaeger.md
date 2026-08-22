[TECH] Jaeger
[OBJ] Open-source distributed tracing platform for monitoring and troubleshooting microservices transactions, based on OpenTelemetry and the Jaeger storage/query UI ecosystem.
[RULES]
1. [REQ] Instrument services with OpenTelemetry SDK emitting OTLP traces to the Jaeger Collector (OTLP gRPC port 4317 or HTTP port 4318); legacy Jaeger clients are deprecated.
2. [REQ] Configure the Jaeger Collector with a storage backend (Badger for dev, Elasticsearch/OpenSearch for prod, Cassandra for large-scale, or Kafka for streaming ingestion).
3. [REQ] Use adaptive sampling (remote sampling) via the Jaeger Collector sampling endpoint; configure service-level sampling strategies in a JSON config served from the Collector.
4. [REQ] Set `SAMPLING_TYPE=ratelimiting` or `SAMPLING_TYPE=probabilistic` with appropriate `SAMPLING_PARAM` for head-based sampling; use tail-based sampling in the OTel Collector for error/slow trace retention.
5. [REQ] Enable span metrics via the Jaeger `spanmetrics` processor to derive RED metrics (Rate, Errors, Duration) from traces and export to Prometheus.
6. [REQ] Deploy Jaeger with the Jaeger Operator on Kubernetes; use the `Jaeger` CRD to define storage, ingress, sampling, and UI configuration declaratively.
7. [REQ] Use the Jaeger UI trace comparison feature to diff traces across baseline and anomalous runs; use the dependency graph for service topology visualization.
8. [REQ] Configure retention policies per storage backend (TTL for Cassandra, ILM for Elasticsearch, `badger.ttl` for Badger) to control storage growth.
9. [CMD] Use `jaegerctl` CLI for admin operations: `jaegerctl archive` for archive management, `jaegerctl sampling` for sampling strategy updates.
10. [CMD] Use `kubectl port-forward svc/jaeger-query 16686` to access the Jaeger UI locally for debugging.
11. [CMD] Use the Jaeger UI `/api/traces?service=<name>&operation=<op>&limit=20` REST API for programmatic trace retrieval and CI smoke tests.
12. [PROHIBIT] Never use the Badger storage backend in production — it is embedded and single-node; use Elasticsearch, Cassandra, or Kafka+Ingester for HA.
13. [PROHIBIT] Never use legacy Jaeger client libraries for new instrumentation — use OpenTelemetry SDKs; Jaeger clients are in maintenance mode and will be deprecated.
14. [PROHIBIT] Never run the Jaeger Collector without resource limits (CPU/memory) in Kubernetes — trace ingestion spikes can cause OOM kills and data loss.
15. [PROHIBIT] Never disable sampling in high-traffic production environments — 100% sampling overwhelms storage and query backends; use adaptive or tail-based sampling.
[COMPAT]
- v1.55.x: OTLP ingestion GA, adaptive sampling via OTel Collector, spanmetrics connector
- v1.60.x: Jaeger v2 (OTel Collector distribution) preview, improved Elasticsearch ILM support
- v1.62.x: Jaeger v2 GA, unified OTel Collector-based architecture, deprecation of all-in-one for prod
[REFS]
- https://www.jaegertracing.io/docs/
- https://www.jaegertracing.io/docs/latest/architecture/
- https://www.jaegertracing.io/docs/latest/sampling/
- https://github.com/jaegertracing/jaeger-operator
