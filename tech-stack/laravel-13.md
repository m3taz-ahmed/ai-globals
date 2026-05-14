# Laravel 13.x Strict Standards
> [!NOTE]
> **STATUS:** STABLE — Released March 17, 2026. Zero breaking changes from Laravel 12.
> **PHP:** Minimum 8.3. **Recommended runtime: PHP 8.4** (required for 13.3+ full compatibility).

## 1. NATIVE TYPES & ARCHITECTURE
- **Native PHP Attributes:** Replace legacy array/property configurations with native PHP attributes across Models, Controllers, Jobs, Events, and Listeners. This is the L13 default — embrace it.
- **Data Objects (DTOs):** Prefer typed Data Transfer Objects using PHP 8.4 asymmetric visibility (`public private(set) string $value;`) over raw arrays for all inter-layer communication.
- **Strict Typing:** Every file MUST declare `strict_types=1`. No exceptions.

## 2. CONTEXT API (Distributed Tracing)
- **Tracing Mandate:** ALWAYS inject a correlation ID into `Context` at the entry point of every request and job. Log channels, Horizon jobs, and Reverb broadcasts MUST propagate this ID.
- **Tenant Context:** In multi-tenant applications, store `tenant_id` in `Context` so it auto-propagates through queued jobs and background tasks.
- **Auto-propagation:** Context propagates automatically through queued jobs, events, and notifications — no manual threading required.

```php
// In middleware — set once, propagates everywhere
Context::add('trace_id', (string) Str::uuid());
Context::add('tenant_id', $request->user()?->tenant_id);
```

## 3. LEAN CORE & BOOTSTRAPPING
- **Minimal Skeleton:** All infrastructure bindings go inside `bootstrap/app.php`. Service providers must be strictly compartmentalized to their domain.
- **Zero Dead Providers:** Remove any service provider not actively bootstrapping something. Every provider adds boot overhead under Octane.
- **Lazy Loading:** Mark non-critical providers with deferred loading.

## 4. FIRST-PARTY AI SDK (`laravel/ai`)
- **Native Vector Search:** Use `whereVectorSimilarTo()` via the AI SDK. NEVER roll a custom pgvector query builder.
- **Streaming Responses:** ALWAYS use `->stream()` for all user-facing LLM outputs. Never await a full completion for a conversational UI.
- **Passkey Auth:** Enforce Laravel 13's native Passkey authentication for all high-privilege AI administrative actions.
- **Separate Rate Limits:** AI endpoints MUST have their own rate limiter, separate from general API throttling.
- **Ref:** See `tech-stack/laravel-ai.md` for full AI SDK implementation patterns.

## 5. QUALITY-OF-LIFE APIS (New in L13)
- **`Cache::touch($key, $ttl)`:** Update a cache entry's TTL without reading or re-computing its value. Use for "heartbeat" keepalives on expensive computations.
- **`JSON:API Resources`:** Use native JSON:API resource support for standardized API responses on public-facing endpoints.
- **Enhanced Reverb:** Laravel Reverb now supports additional database drivers for scalable WebSocket state across multiple nodes.

---

## ✅ LARAVEL 13 COMPLIANCE CHECK (Mandatory)
- [ ] **PHP 8.4:** Is the project targeting PHP 8.4 as the runtime?
- [ ] **Context API:** Is a trace/correlation ID injected into `Context` for every request?
- [ ] **DTOs:** Are inter-layer data structures using typed DTOs, not raw arrays?
- [ ] **AI SDK:** Is `laravel/ai` the ONLY interface to LLM providers?
- [ ] **Dead Providers:** Are all service providers actively used and lazy-loaded where possible?
