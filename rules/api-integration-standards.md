# External API Integration Standards

> All external API integrations MUST follow these standards to ensure resilience, security, and maintainability.

## 1. HTTP CLIENT

- **Use Laravel HTTP Client** (`Http::`) — the Guzzle wrapper. Never use raw `cURL` or direct Guzzle instantiation.
- **Set explicit timeouts** on every request: `connectTimeout(5)` and `timeout(30)` as defaults. Adjust per-integration based on documented SLA.
- **Create dedicated Service classes** per integration (e.g., `DaftraApiService`, `PaymentGatewayService`). Never scatter API calls across Controllers or Jobs directly.
- **Use Base URL configuration:** Store base URLs in `config/services.php`, never hardcode in Service classes.

```php
// config/services.php
'daftra' => [
    'base_url' => env('DAFTRA_API_URL'),
    'api_key'  => env('DAFTRA_API_KEY'),
    'timeout'  => 30,
],
```

## 2. ERROR HANDLING

- **Wrap ALL external calls** in try/catch with specific exception types:
  - `ConnectionException` — network failures, DNS issues, timeouts.
  - `RequestException` — non-2xx HTTP responses.
  - Application-specific exceptions for business logic failures.
- **Never let external failures crash the user experience.** Implement graceful degradation:
  - Return cached data if available.
  - Queue the operation for retry.
  - Show a user-friendly error message.
- **Log request/response for debugging** — but ALWAYS sanitize sensitive data (tokens, passwords, PII) before logging.

```php
// ✅ Correct pattern
try {
    $response = Http::daftra()->get('/invoices/' . $id);
    $response->throw(); // throws on non-2xx
    return $response->json();
} catch (ConnectionException $e) {
    Log::error('Daftra API unreachable', ['error' => $e->getMessage()]);
    throw new ExternalServiceUnavailableException('Daftra', $e);
} catch (RequestException $e) {
    Log::error('Daftra API error', [
        'status' => $e->response->status(),
        'body'   => Str::limit($e->response->body(), 500),
    ]);
    throw new ExternalServiceException('Daftra', $e);
}
```

## 3. RETRY & RESILIENCE

- **Implement retry with exponential backoff** for transient failures (5xx, timeouts):
  - `->retry(3, function (int $attempt) { return $attempt * 1000; })` — 1s, 2s, 3s delays.
  - Only retry on transient errors (5xx, 429). Never retry on 4xx (client errors).
- **Circuit Breaker pattern** for critical integrations:
  - Track consecutive failures. After N failures (e.g., 5), open the circuit — skip API calls and return fallback for a cooldown period.
  - Use a cache key to track circuit state (e.g., `circuit:daftra:open`).
- **Queue external API calls** when real-time response is not required. This isolates the user experience from external latency.
- **Set `ShouldBeUnique`** on jobs that call external APIs to prevent duplicate operations during retries.

## 4. AUTHENTICATION & SECRETS

- **Store ALL API keys and secrets in `.env`** — never hardcode in source code, configs, or comments.
- **Use OAuth tokens with automatic refresh** where the external API supports it. Store refresh tokens encrypted in the database.
- **Rotate API keys quarterly** at minimum. Document the rotation procedure per integration.
- **Use scoped/least-privilege tokens** — request only the permissions the integration actually needs.
- **Register HTTP macros** in `AppServiceProvider` for reusable authenticated clients:

```php
Http::macro('daftra', function () {
    return Http::baseUrl(config('services.daftra.base_url'))
        ->withToken(config('services.daftra.api_key'))
        ->timeout(config('services.daftra.timeout'))
        ->acceptJson()
        ->asJson();
});
```

## 5. WEBHOOK HANDLING

- **Verify webhook signatures** before processing. Reject unsigned or invalid payloads with HTTP 403.
- **Make webhook handlers idempotent.** Use a unique event ID to detect and skip duplicate deliveries.
- **Store the raw webhook payload** (in a `webhook_logs` table or similar) BEFORE processing. This enables replay and debugging.
- **Process webhooks asynchronously:** Receive → store → respond 200 → dispatch a Job to process. Never do heavy logic in the webhook controller.
- **Set a short response timeout:** Webhook senders expect a fast response (< 5 seconds). Return 200/202 immediately and process in the background.

## 6. RESPONSE CACHING

- **Cache stable API responses** to reduce external calls and improve latency:
  - Static reference data (categories, currencies, settings): TTL 1–24 hours.
  - Entity data (invoices, clients): TTL 5–30 minutes, with event-driven invalidation.
- **Use tagged caching** for easy invalidation: `Cache::tags(['daftra', 'invoices'])->remember(...)`.
- **Never cache authentication tokens or user-specific sensitive data** beyond their natural expiry.

## 7. VERSIONING & DOCUMENTATION

- **Pin the API version** in every integration (via URL path or header). Never rely on the "latest" version implicitly.
- **Document each integration** in a dedicated section of the project's README or a `docs/integrations/` directory:
  - API name, version, and base URL.
  - Authentication method.
  - Endpoints used and their purpose.
  - Rate limits and quotas.
  - Error codes and handling strategy.
  - Contact/support for the external service.
