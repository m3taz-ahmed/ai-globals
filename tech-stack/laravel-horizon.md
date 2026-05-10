# Tech-Stack: Laravel Horizon

> [!NOTE]
> **TRIGGER:** LOAD ON background jobs, queue configuration, async processing.
> **SCOPE:** Laravel Horizon (Laravel 12/13).

## 1. Queue Architecture
- Segregate queues by workload type (e.g., `high`, `default`, `low`, `notifications`, `webhooks`).
- Configure supervisors to handle specific queues with appropriate worker counts.
- Utilize Horizon's auto-scaling (balancing strategies: `simple`, `auto`, `false`) based on queue pressure.

## 2. Job Patterns & Tracking
- Implement job batching for large, parallel tasks (e.g., CSV imports) and track completion/failures via callbacks.
- Use rate limiting (`Redis::funnel` or `Redis::throttle`) for jobs hitting third-party APIs.
- Define retry strategies (e.g., exponential backoff) and specific `failed` methods for graceful degradation.
- Ensure multi-tenant queue isolation when processing tenant-specific data.

## 3. Laravel 12/13 Syntax & Context
- Use native PHP 8.4+ types and strict DTOs for job payloads.
- Leverage the Laravel Context API (`Context::add()`) to append trace IDs or tenant IDs automatically to job logs.

## 4. Hard Constraints
- NEVER dispatch long-running synchronous code inside web requests; push it to a queue.
- NEVER rely on global state or singletons across different jobs.
- ALWAYS make jobs idempotent (safe to retry multiple times without side effects).

---

## ✅ LARAVEL HORIZON COMPLIANCE CHECK (Mandatory)
- [ ] **Idempotency:** Are all queued jobs safe to run multiple times?
- [ ] **Observability:** Is the Context API used to trace jobs back to requests/users?
- [ ] **Scaling:** Are queues properly segregated and auto-scaling configured?
