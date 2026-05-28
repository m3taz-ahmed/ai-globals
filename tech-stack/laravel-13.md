# Laravel 13.x Strict Standards
> [!NOTE]
> Status: Stable (March 2026). PHP 8.3 min, 8.4 recommended.

## Native Types & Architecture
- **Attributes:** Use native PHP attributes on Models, Controllers, Jobs, Events, Listeners.
- **DTOs:** Use typed DTOs with PHP 8.4 asymmetric visibility (`public private(set) string $val;`) for inter-layer data. ⛔ raw arrays.
- **Strict:** Every file must declare `strict_types=1`.

## Context API (Tracing & Tenancy)
- **Trace ID:** Inject correlation/trace ID into `Context` at HTTP/Job entry points. Log channels, Horizon, and Reverb must propagate it.
- **Tenancy:** Store `tenant_id` in `Context` to auto-propagate to queue tasks.
- **Setup:** `Context::add('trace_id', (string) Str::uuid());`

## Bootstrap & Engine
- **App Setup:** Bind infrastructure in `bootstrap/app.php`. Compartmentalize service providers.
- **Lean Octane:** ⛔ dead/unused service providers. Mark non-critical providers as deferred.

## First-Party AI Integration (`laravel/ai`)
- **RAG:** Use native `whereVectorSimilarTo()` query. ⛔ custom pgvector builders.
- **SSE:** Stream chat/LLM output via `->stream()`. ⛔ await full completion.
- **Auth:** Passkey authentication for AI administrative tasks.
- **Throttling:** Separate, dedicated rate limiters for AI routes.

## Features
- **TTL update:** Use `Cache::touch($key, $ttl)` for heartbeats.
- **JSON:API:** Use native JSON:API response structures for public endpoints.
- **Reverb:** WebSockets scale across DB-backed state.
