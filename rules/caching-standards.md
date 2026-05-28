# Caching Standards & Topology
> [!NOTE]
> Trigger: performance optimization, cache implementation, state management, Redis configuration.

## Caching Architecture `[PERF-06]`
- **Tiered Cache:** Split L1 (memory/Octane) and L2 (Redis 7).
- **Key naming:** `{tenant_id}:{domain}:{entity}:{id}:{variant}` (e.g., `tenant:42:user:profile:1001:full`).
- **TTL Policies:** Volatile (5-15m), Computed (1-6h), Static (12-24h).
- **Isolation:** Cache keys MUST scope to tenant/user.

## Advanced Patterns `[PERF-07]`
- **Stampede Prevention:** Use atomic locking (`Cache::lock()`) or early expiration.
- **Serialization & Compression:** Use igbinary/MessagePack, compress payloads >1KB.
- **Warming & Invalidation:** Warmer jobs on deploy; event-driven cache invalidation.

## Redis Resilience & Degradation `[PERF-08]`
- **Sentinel/Cluster:** Sentinel for small failovers, Cluster mode for >25GB.
- **Graceful Fallback:** Circuit breaker must fall back to DB on Redis failure. ⛔ crash application.
