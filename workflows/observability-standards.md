[WORKFLOW] observability-standards
[OBJ] Observability & Monitoring Standards.
[RULES]
1. [REQ] Logging `[OBS-01]`: JSON in production. Correct RFC levels. Context is mandatory. NO PII or secrets.
2. [REQ] Tracing: OpenTelemetry (OTel) with `trace_id` propagation.
3. [REQ] Health `[OBS-02]`: Expose `GET /health` checking DB, cache, queue, disk.
4. [REQ] Metrics: Track p95 response (<2s), error rate (<1%), queue depth, DB connections, memory.
5. [REQ] Errors `[OBS-03]`: Sentry/Bugsnag. Triage within 24h.
6. [REQ] Alerts: Tiered (Critical/High/Warn/Info). No alert fatigue. Rate limit alerts.
7. [REQ] Local: Laravel Telescope / Debugbar. Enable `Model::shouldBeStrict()`.
8. [REQ] Audits `[OBS-04]`: Audit state-changes (Who, What, When, Before/After). Min 12mo retention. NEVER delete audit logs.
