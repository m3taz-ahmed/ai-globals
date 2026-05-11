# Laravel 13.x Strict Standards
> [!IMPORTANT] Laravel 13 is STABLE (Released March 2026). Minimum requirement is PHP 8.3+.

## 1. NATIVE TYPES & ARCHITECTURE
- **Native PHP Attributes:** Replace legacy array/property configurations with native PHP attributes across Models, Controllers, Jobs, and Listeners.
- **Data Objects:** Prefer typed Data Transfer Objects (DTOs) over raw arrays for inter-layer communication, utilizing PHP 8.3/8.4+ typing.

## 2. CONTEXT API
- **Tracing:** Utilize the native `Context` API deeply for logging and tracing across background jobs and requests.
- **Propagation:** Context automatically propagates through queued jobs, events, and notifications. Use it for correlation IDs and user context.

## 3. LEAN CORE & BOOTSTRAPPING
- **Minimal Skeleton:** Exploit the minimal skeleton. Keep all infrastructure bindings in `bootstrap/app.php` and service providers strictly compartmentalized.
- **Zero Dead Providers:** Remove any service providers that are not actively used. Every provider adds boot overhead.

## 4. AI & LLM INTEGRATION
- **Native Vector Search:** Utilize Laravel 13's native semantic/vector search capabilities (e.g., `whereVectorSimilarTo()`) instead of custom implementations.
- **Passkey Authentication:** Enforce Laravel 13's native Passkey authentication for high-privilege AI administrative actions.
- **Rate Limiting:** Apply separate token-based rate limits for AI endpoints.
- **Streaming Responses:** Use Laravel's streaming response capabilities for LLM outputs to reduce time-to-first-token.
