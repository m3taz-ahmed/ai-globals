[TECH] laravel-octane
[OBJ] Laravel Octane Backend Scaling.
[RULES]
1. [REQ] Driver: Default FrankenPHP (HTTP/3). RoadRunner (gRPC/enterprise). Swoole (WebSockets/coroutines).
2. [REQ] Memory Mgmt: Set `--max-requests` (500-2000) explicitly to prevent leaks. Log peak memory. Bind request-state as `scoped` (not `singleton`).
3. [REQ] Perf: Use `Octane::concurrently`, `Octane::cache`. Persistent DB connections.
4. [REQ] Deploy: `octane:reload` for zero-downtime. Configure health checks `/up` and drain periods.
5. [PROHIBIT] Constraints: NEVER use `env()` outside config. NEVER leak DB connections. NEVER deploy without `--max-requests`.
