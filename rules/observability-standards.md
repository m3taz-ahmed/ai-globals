# Observability & Monitoring Standards

> A system without observability is a system operated by luck. Every production application MUST be observable: logging, monitoring, alerting, and health checks are non-negotiable.

## 1. STRUCTURED LOGGING

- **Format:** Use structured (JSON) logging in production. Human-readable format is acceptable in local development only.
- **Log Levels (RFC 5424) — use correctly:**
  - `DEBUG` — Detailed diagnostic info. **Local/staging only**, never in production.
  - `INFO` — Normal operational events: user login, job dispatched, payment processed.
  - `WARNING` — Unexpected but recoverable: deprecated API used, cache miss on expected key, slow query detected.
  - `ERROR` — Failures requiring attention: external API failure, validation exception in an unexpected place, job failure.
  - `CRITICAL` — System-level failures: database connection lost, queue worker crash, disk full.
- **Context is mandatory.** Every log entry MUST include relevant context. Bare messages are useless:

```php
// ❌ Useless
Log::error('Invoice creation failed');

// ✅ Actionable
Log::error('Invoice creation failed', [
    'booking_id' => $booking->id,
    'client_id'  => $booking->client_id,
    'error'      => $e->getMessage(),
    'trace'      => Str::limit($e->getTraceAsString(), 1000),
]);
```

- **Sensitive data prohibition:** NEVER log passwords, API keys, tokens, credit card numbers, or raw PII. Mask or omit them.
- **Correlation IDs:** For request tracing across services, attach a unique `request_id` (UUID) to every log entry within a single HTTP request or job execution. Use middleware to generate and propagate it.

## 2. APPLICATION MONITORING

- **Health Endpoint:** Every application MUST expose a `GET /health` endpoint returning:
  - HTTP `200 OK` with a JSON body when healthy.
  - HTTP `503 Service Unavailable` when critical dependencies are down.
  - Check: database connectivity, cache (Redis) connectivity, queue connectivity, disk space.

```json
{
  "status": "healthy",
  "checks": {
    "database": "ok",
    "cache": "ok",
    "queue": "ok",
    "disk": "ok"
  },
  "timestamp": "2026-05-01T20:00:00Z"
}
```

- **Key Metrics to Track:**
  - **Response Time:** p50, p95, p99 per route. Alert if p95 > 2 seconds.
  - **Error Rate:** 5xx responses as a percentage of total requests. Alert if > 1%.
  - **Queue Depth:** Number of pending jobs per queue. Alert if > 100 pending for > 5 minutes.
  - **Queue Processing Time:** Average time per job. Alert if > 60 seconds.
  - **Failed Jobs:** Count in `failed_jobs` table. Alert on any new failed job.
  - **Database Connections:** Active connection count. Alert if approaching pool limit.
  - **Disk Usage:** Alert if > 85% on any mount point.
  - **Memory Usage:** PHP worker memory. Alert if consistently > 80% of limit.

## 3. ERROR TRACKING

- **Use a dedicated error tracking service** (Sentry, Bugsnag, Flare, or equivalent) in all non-local environments.
- **Configuration:**
  - Capture all unhandled exceptions automatically.
  - Attach user context (user ID, role) to error reports — but never PII.
  - Group similar errors to prevent alert fatigue.
  - Set up release tracking to correlate errors with deployments.
- **Operational Discipline:**
  - New errors must be triaged within 24 hours: assign, prioritize, or mark as expected.
  - Recurring unresolved errors must be reviewed in the monthly audit.
  - Resolved errors should be verified as actually fixed — not just marked and forgotten.

## 4. ALERTING STRATEGY

- **Tiered Alerting — don't alert on everything:**

| Severity | Condition | Action | Channel |
|---|---|---|---|
| 🔴 CRITICAL | App down, DB unreachable, data loss risk | Immediate page/call | SMS, Phone |
| 🟠 HIGH | Error rate > 5%, queue stalled, disk > 90% | Respond within 1 hour | Slack, Email |
| 🟡 WARNING | Error rate > 1%, p95 > 2s, failed job | Respond within 24 hours | Slack |
| ℹ️ INFO | Deployment completed, scheduled task ran | No action needed | Log only |

- **Anti-alert-fatigue rules:**
  - Never alert on expected behavior (scheduled maintenance, known transient errors).
  - Use rate limiting on alerts — max 1 alert per unique issue per 15 minutes.
  - Review and prune alert rules monthly. If an alert never fires, consider removing it. If it fires constantly, fix the root cause or adjust the threshold.

## 5. DEVELOPMENT OBSERVABILITY (LOCAL)

- **Laravel Telescope:** Install in local and staging environments for:
  - Request inspection (headers, payload, response).
  - Query monitoring (detect N+1, slow queries).
  - Job and event monitoring.
  - Exception inspection with full context.
- **Laravel Debugbar:** Use in local development for per-request performance profiling (query count, memory, time).
- **`Model::shouldBeStrict()`:** Enable in local/staging `AppServiceProvider` to catch lazy loading, silently discarded attributes, and invalid attribute access.
- **Slow Query Log:** Enable MySQL slow query log (threshold: 500ms) in staging. Review weekly.

## 6. AUDIT TRAILS

- **State-changing operations MUST be audited:** Create, Update, Delete on business entities.
- **Audit record contents:**
  - Who: User ID and role.
  - What: Action performed and the model/entity affected.
  - When: Timestamp (UTC).
  - Before/After: Old values and new values for updates.
- **Storage:** Use a dedicated `audit_logs` table or a package like `spatie/laravel-activitylog`.
- **Retention:** Keep audit logs for a minimum of 12 months. Archive to cold storage after that.
- **Never delete audit logs** in response to a user request. They are a compliance and forensic resource.
