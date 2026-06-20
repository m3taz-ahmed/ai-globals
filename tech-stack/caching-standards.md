[TECH] caching-standards
[OBJ] Caching Standards & Topology.
[RULES]
1. [REQ] Architecture `[PERF-06]`: Tiered (L1 Mem, L2 Redis). Key format: `{tenant_id}:{domain}:{entity}:{id}:{variant}`. Scope to tenant/user.
2. [REQ] Resilience `[PERF-07]`: Stampede prevention (`Cache::lock()`). Event-driven invalidation. igbinary compression >1KB payloads.
3. [REQ] Fallback `[PERF-08]`: Graceful fallback to DB on Redis failure via Circuit Breaker. Redis Sentinel/Cluster.
