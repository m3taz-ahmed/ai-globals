# Tech-Stack: Caching Standards

> [!NOTE]
> **TRIGGER:** LOAD ON performance optimization, cache implementation, state management, Redis configuration.
> **SCOPE:** L1/L2 Caching, Redis 7, Octane Cache, Cache Topology & Resilience.

## 1. Caching Architecture & Topology

- Differentiate between **L1 Cache** (request-scoped, memory array, or Octane Cache) and **L2 Cache** (distributed, Redis 7).
- Establish strict Cache Key naming conventions: `{tenant_id}:{domain}:{entity}:{id}:{variant}` (e.g., `tenant:42:user:profile:1001:full`).
- Define explicit TTL (Time-To-Live) policies tailored to the data type:
  - **Volatile data** (user sessions, CSRF tokens): 5–15 minutes.
  - **Computed data** (dashboard aggregates, reports): 1–6 hours.
  - **Static config** (feature flags, tenant settings): 12–24 hours.
- Choose the appropriate caching pattern per use case:
  - **Cache-Aside (Lazy Loading):** Default for read-heavy data. Application checks cache, falls through to DB on miss.
  - **Write-Through:** For data requiring strong consistency. Write to cache and DB simultaneously.
  - **Write-Behind (Write-Back):** For write-heavy, latency-sensitive paths. Write to cache immediately, asynchronously persist to DB via queue.

## 2. Advanced Caching Patterns

- Implement **Cache Warming** strategies for critical paths (e.g., warming the dashboard cache via a scheduled job after deployments or data migrations).
- Prevent **Cache Stampedes** using atomic locking (`Cache::lock()`) when regenerating expensive cached data. Use probabilistic early expiration (PER) for ultra-high-traffic keys.
- Ensure **Tenant-Scoped Cache Isolation** to prevent cross-tenant data leaks. All multi-tenant cache keys MUST include the tenant identifier.
- Implement **Event-Driven Cache Invalidation** (e.g., clearing the user profile cache when the `UserUpdated` event fires). Never rely solely on TTL for mutable data.
- For large cached payloads (>1KB), apply **compression** (LZ4 or zstd) before storing in Redis to reduce memory footprint and network transfer.
- Use efficient **serialization formats** (MessagePack or `igbinary`) instead of PHP's native `serialize()` for reduced payload size and faster deserialization in Octane workers.

## 3. Redis 7 High Availability & Resilience

- Deploy Redis in **Cluster mode** (minimum 3 primary + 3 replica nodes) for production workloads exceeding 25GB or requiring cross-shard distribution.
- For smaller deployments, use **Redis Sentinel** (minimum 3 sentinels) for automatic failover.
- Implement **graceful cache degradation**: if Redis is unreachable, the application MUST fall through to the database transparently rather than returning errors. Use circuit breakers on the cache layer.
- Configure Redis `maxmemory-policy` to `allkeys-lru` or `volatile-lru` depending on whether all keys have TTLs. Monitor eviction rates; sustained evictions indicate undersized cache.
- Enable Redis **persistence** (RDB snapshots + AOF) for warm-restart after failures, preventing cold-cache thundering herd on recovery.

## 4. Observability

- Monitor **Cache Hit Rate** per cache domain (target: >90% for L2 cache). Hit rates below 80% indicate misconfigured TTLs or missing warming strategies.
- Monitor Redis memory usage, eviction rate, connected clients, and command latency via Datadog, CloudWatch, or Redis's built-in `INFO` metrics.
- Alert on sustained cache miss spikes that correlate with database load increases.

## 5. Hard Constraints

- NEVER cache tenant-specific data without the tenant ID in the cache key.
- NEVER cache large, unbounded datasets (e.g., full table dumps) that could overwhelm Redis memory.
- NEVER use PHP's `serialize()` for cache values in Octane environments; use MessagePack or `igbinary` to avoid deserialization vulnerabilities and improve performance.
- ALWAYS set a TTL on cache keys unless they are system-level, explicitly managed flags.
- ALWAYS implement a cache fallback path to the database; the application must never hard-fail on cache unavailability.

---

## ✅ CACHING STANDARDS COMPLIANCE CHECK (Mandatory)
- [ ] **Isolation:** Are cache keys properly scoped to the tenant or user?
- [ ] **Resilience:** Is cache stampede prevention (locking or PER) implemented for heavy queries?
- [ ] **Degradation:** Does the application gracefully degrade to DB-direct queries when Redis is unavailable?
- [ ] **Lifecycle:** Are event-driven invalidation hooks implemented for mutable cached data?
- [ ] **Serialization:** Is an efficient serialization format (MessagePack/igbinary) configured instead of native `serialize()`?
- [ ] **HA:** Is Redis deployed with Sentinel or Cluster mode for automatic failover?
- [ ] **Observability:** Are cache hit rates monitored with alerts for sustained miss spikes?
