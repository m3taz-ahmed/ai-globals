# Tech-Stack: Laravel Octane

> [!NOTE]
> **TRIGGER:** LOAD ON backend scaling, API performance tuning, Laravel deployment, Octane configuration.
> **SCOPE:** Laravel 12/13 with FrankenPHP, RoadRunner, or Swoole.

## 1. Driver Selection Matrix

| Criteria | FrankenPHP | RoadRunner | Swoole |
|---|---|---|---|
| **Best For** | Simplified deployment, HTTP/3, single-binary | High-throughput APIs, mature plugin ecosystem | WebSockets, coroutines, high-concurrency I/O |
| **Architecture** | PHP embedded in Caddy (Go) | Go process managing PHP worker pool | C extension with event loop |
| **Deployment** | Single binary, automatic HTTPS/TLS | Binary + worker pool config | Requires `swoole` PECL extension |
| **HTTP/3 Support** | ✅ Native (via Caddy) | ❌ Requires external proxy | ❌ Requires external proxy |
| **Memory Efficiency** | High (sensitive to state leaks) | High (robust process supervision) | Moderate (coroutine overhead) |
| **Production Maturity** | Rapidly maturing (2025+) | Battle-tested, enterprise-grade | Battle-tested, niche use cases |

**Decision Rule:** Default to **FrankenPHP** for new projects (simplicity + HTTP/3). Use **RoadRunner** for complex architectures requiring gRPC or advanced process orchestration. Reserve **Swoole** for WebSocket-heavy or real-time applications requiring native coroutines.

## 2. Worker Lifecycle & Memory Management

- Understand that Laravel Octane boots the framework once and keeps it in memory. Requests are handled by worker processes.
- Prevent memory leaks by avoiding static state or appending to global arrays.
- Be careful with service container bindings: use `scoped` or `bind` instead of `singleton` for request-specific state.
- **Set `--max-requests` explicitly** in production (recommended: 500–2000). This forces graceful worker restarts to reclaim leaked memory. Never rely on defaults.
- **Monitor memory growth per worker:** Use `memory_get_peak_usage()` logging per request to identify endpoints causing abnormal memory growth.
- **Baseline test:** Compare memory at `--max-requests=1` (FPM-like) vs production settings. If stable at 1 but grows at 500+, a leak exists.
- Verify all third-party packages are Octane-compatible; some assume destruction after every request and fail to clean up state.

## 3. Concurrency & Performance

- Use Octane's Concurrent Tasks (`Octane::concurrently`) to execute multiple independent operations simultaneously.
- Utilize Octane's Cache (`Octane::cache()`) for ultra-fast, worker-memory caching (L1 Cache layer).
- Register flush callbacks (`Octane::flush`) to reset stateful third-party libraries or singletons between requests.
- Use tick callbacks (`Octane::tick`) carefully for background processing without blocking the request.
- Enable **persistent database connections** (`PDO::ATTR_PERSISTENT => true`) with proper timeout configuration to leverage Octane's long-lived worker model.
- For FrankenPHP: leverage built-in HTTP/2 push and HTTP/3 (QUIC) for reduced latency on API responses.

## 4. Graceful Deployment & Reload

- Use `php artisan octane:reload` for zero-downtime code deployments, ensuring workers are replaced without dropping active connections.
- In containerized environments (ECS/EKS), configure health checks against Octane's `/up` endpoint and use rolling deployments with proper drain periods.
- Set container `stopGracePeriod` (ECS: `stopTimeout`) to allow in-flight requests to complete before worker termination.
- NEVER restart the Octane process by killing the container abruptly; always use the graceful reload mechanism first.

## 5. PHP 8.4+ & Laravel 12/13 Syntax

- Use property hooks and asymmetric visibility for DTOs and models (e.g., `public private(set) string $name;`).
- Use typed class constants.
- Ensure all custom service providers are Octane-compatible.
- Leverage Laravel 13's zero-breaking-change upgrade path for seamless version transitions.

## 6. Hard Constraints

- NEVER use `env()` outside of configuration files; use `config()` since env vars are cached and workers don't reload them dynamically.
- NEVER leak database connections; ensure all transactions are closed and resources freed.
- NEVER deploy Octane without setting `--max-requests`; unbounded worker lifetimes guarantee memory bloat.
- ALWAYS test the application locally under Octane (`php artisan octane:start`) to catch state-leak bugs.
- ALWAYS profile memory during development using `php artisan octane:profile-memory` or equivalent tooling.

---

## ✅ LARAVEL OCTANE COMPLIANCE CHECK (Mandatory)
- [ ] **Driver Selection:** Is the chosen Octane driver (FrankenPHP/RoadRunner/Swoole) justified by the project's architectural requirements?
- [ ] **State Safety:** Are singletons and static variables free from request-specific state?
- [ ] **Memory Management:** Are flush callbacks registered, and is `--max-requests` explicitly configured for production?
- [ ] **Memory Monitoring:** Is per-worker memory growth being logged and baselined?
- [ ] **Graceful Deployment:** Is `octane:reload` integrated into the CI/CD pipeline for zero-downtime deployments?
- [ ] **Modern PHP:** Are PHP 8.4+ and Laravel 12/13 syntaxes utilized effectively within the workers?
