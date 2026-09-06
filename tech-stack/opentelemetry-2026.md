[TECH] OpenTelemetry + OpenInference for AI Agents 2026
[OBJ] OTel native tracing for LLM/agent calls + OpenInference span attributes (LLM, tool, retrieval, guardrail). First-class GUARDRAIL span. Default telemetry standard for AI observability.
[RULES]
1. [REQ] Use OpenTelemetry (OTel) native tracing for all LLM/agent calls — `@tracer.start_as_current_span("llm.call")` around inference.
2. [REQ] Use OpenInference span attributes for semantic enrichment: `llm.*`, `tool.*`, `retrieval.*`, `guardrail.*`, `agent.*`.
3. [REQ] Use `arize-phoenix-otel>=0.16.0` for Phoenix-compatible OTel export — `phoenix.otel.register()`.
4. [REQ] Use first-class `GUARDRAIL` span kind — wrap Guardrails AI / validation calls in `span_kind=GUARDRAIL` spans.
5. [REQ] Set span attributes: `llm.model_name`, `llm.provider`, `llm.token_count.prompt`, `llm.token_count.completion`, `llm.invocation_parameters`.
6. [REQ] Set `retrieval.*` attributes for RAG: `retrieval.query`, `retrieval.documents`, `retrieval.source`.
7. [REQ] Set `tool.*` attributes for tool calls: `tool.name`, `tool.input`, `tool.output`, `tool.error`.
8. [REQ] Use OTel `SpanProcessor` + `Exporter` pipeline — batch processor for production, simple for dev.
9. [REQ] Use `OTEL_EXPORTER_OTLP_ENDPOINT` env var for collector endpoint — never hardcode in source.
10. [REQ] Use trace context propagation across agent boundaries — W3C TraceContext headers.
11. [REQ] Use `@tracer.start_as_current_span()` context manager — never manual span creation without context.
12. [REQ] Use metrics for token usage, latency, error rates — `meter.create_counter("llm.tokens")`, `meter.create_histogram("llm.latency")`.
13. [PROHIBIT] Never use custom logging for LLM observability — use OTel + OpenInference attributes.
14. [PROHIBIT] Never omit `GUARDRAIL` spans — guardrail validation must be traced as first-class spans.
15. [PROHIBIT] Never hardcode collector endpoint — use env vars.
16. [PROHIBIT] Never use `arize-phoenix-otel < 0.16.0` — older versions lack GUARDRAIL span support.
17. [CMD] `pip install opentelemetry-sdk opentelemetry-exporter-otlp arize-phoenix-otel>=0.16.0` — install.
18. [CMD] `OTEL_EXPORTER_OTLP_ENDPOINT=http://collector:4317 python app.py` — run with collector.
19. [CMD] `phoenix.otel.register()` — register Phoenix OTel in code.
20. [CMD] `opentelemetry-instrument python app.py` — auto-instrument.
[COMPAT]
- OpenTelemetry SDK (latest 2026).
- OpenInference span attributes: LLM, tool, retrieval, guardrail, agent.
- `arize-phoenix-otel>=0.16.0` required for GUARDRAIL span.
- OTLP exporter (gRPC / HTTP).
- W3C TraceContext propagation.
[REFS]
- https://opentelemetry.io/
- https://github.com/Arize-ai/openinference
- https://github.com/Arize-ai/phoenix
- https://opentelemetry.io/docs/specs/otel/
