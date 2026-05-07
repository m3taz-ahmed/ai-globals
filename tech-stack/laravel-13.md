# Laravel 13.x Strict Standards
> [!SPECULATIVE] Laravel 13 is not yet released. Rules are based on community previews and announced roadmap. Verify against official release notes before applying.

## 1. NATIVE TYPES & DTOs
- **PHP 8.5 Native Types:** Rely entirely on PHP 8.5 native types; strip redundant validation rules if handled by DTOs/Value Objects.
- **Data Objects:** Prefer typed Data Transfer Objects over raw arrays for inter-layer communication.

## 2. CONTEXT API
- **Tracing:** Utilize the native `Context` API deeply for logging and tracing across background jobs and requests.
- **Propagation:** Context automatically propagates through queued jobs, events, and notifications. Use it for correlation IDs and user context.

## 3. LEAN CORE & BOOTSTRAPPING
- **Minimal Skeleton:** Exploit the minimal skeleton. Keep all infrastructure bindings in `bootstrap/app.php` and service providers strictly compartmentalized.
- **Zero Dead Providers:** Remove any service providers that are not actively used. Every provider adds boot overhead.

## 4. AI & LLM INTEGRATION
- **Pipeline Routing:** If integrating AI, use standard Laravel pipeline routing for prompt engineering and vector DB interactions.
- **Rate Limiting:** Apply separate rate limits for AI endpoints (token-based, not just request-based).
- **Streaming Responses:** Use Laravel's streaming response capabilities for LLM outputs to reduce time-to-first-token.