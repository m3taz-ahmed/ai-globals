# External API Integration Standards
> [!NOTE]
> Trigger: HTTP client, service creation, webhook handling.

## HTTP Client & Architecture `[API-01]`
- **Tool:** Use Laravel `Http::` wrapper (Guzzle). ⛔ raw `cURL` or direct Guzzle instantiation.
- **Config:** ConnectTimeout default `5s`, Timeout `30s` (adjust per SLA). Base URL/Secrets in `config/services.php` (loaded from `.env`).
- **Encapsulation:** Dedicated Service classes per integration. ⛔ direct API calls in controllers/jobs.
- Register client macros in `AppServiceProvider`:
  ```php
  Http::macro('daftra', fn() => Http::baseUrl(config('services.daftra.base_url'))->withToken(config('services.daftra.api_key'))->timeout(config('services.daftra.timeout')));
  ```

## Error Handling & Resilience `[API-02]`
- **Try/Catch:** Wrap calls in ConnectionException/RequestException checks. ⛔ crash UX on external failure. Gracefully fallback (cache, queue retry, friendly error).
- **Log Sanitization `[SEC-04]`:** Sanitize logs (tokens, passwords, PII) before saving.
- **Retry:** Implement exponential backoff for transient issues (5xx, 429) using `->retry(3, fn($att) => $att * 1000)`. ⛔ retry 4xx errors.
- **Circuit Breaker:** Skip calls and fallback for cooldown after N failures using a cache key.
- **Queueing `[PERF-03]`:** Queue non-real-time calls. Use `ShouldBeUnique` for retry jobs to avoid duplicate execution.

## Webhooks `[API-03]`
- **Signature:** Verify payload signature first. Reject invalid requests (HTTP 403).
- **Idempotency:** Track event IDs to skip duplicates. Store raw payload before processing.
- **Asynchronous:** Receive → store raw payload → respond 200/202 immediately (<5s) → dispatch background processing Job.

## Caching
- **TTL:** Static data: TTL 1-24h. Dynamic entities: TTL 5-30m. Tag caches for invalidation.
- **Storm Avoidance `[API-04]`:** Cache-Retry Interlock: ⛔ attempt retries on cached stale data unless `FORCE_REFRESH` header is present.

## Versioning & Docs
- **Versioning:** Pin API versions in URLs/headers. ⛔ use "latest" implicitly.
- **Docs:** Keep integration details (URLs, auth, rate limits, errors) in project README or `docs/integrations/`.
