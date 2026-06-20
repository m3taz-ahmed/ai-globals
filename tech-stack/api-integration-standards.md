[TECH] api-integration-standards
[OBJ] External API Integration Standards.
[RULES]
1. [REQ] Client `[API-01]`: Laravel `Http::` wrapper. Dedicated Service classes. Macro registration in `AppServiceProvider`.
2. [REQ] Resilience `[API-02]`: Exponential backoff (`->retry`) for 5xx/429. NO retrying 4xx. Implement Circuit Breaker.
3. [REQ] Webhooks `[API-03]`: Verify signature FIRST. Idempotency tracking. Async processing (respond 2xx <5s -> queue job).
4. [REQ] Caching `[API-04]`: Cache-Retry Interlock. Tag caches. TTL 1-24h static, 5-30m dynamic.
5. [REQ] Security `[SEC-04]`: Sanitize logs (strip tokens/PII). Pin API versions explicitly.
