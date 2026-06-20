[TECH] sentry-tracking
[OBJ] Sentry Tracking & Error Monitoring.
[RULES]
1. [REQ] Integration: Next.js + Laravel SDKs. Upload Source Maps (then delete from public). Track Git SHA release versions.
2. [REQ] Context: Bind authenticated user context + `tenant_id`. Record breadcrumbs.
3. [REQ] Performance/AI: Link Sentry Perf to OpenTelemetry. Session Replay (strict privacy mask). AI Autofix pipelines.
4. [PROHIBIT] Constraints: NEVER log PII/sensitive data. NEVER ignore alerts. ALWAYS set reasonable sample rate (`traces_sample_rate = 0.1`).
