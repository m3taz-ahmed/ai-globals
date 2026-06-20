[TECH] redis-7
[OBJ] Redis 7 Caching & Topology.
[RULES]
1. [REQ] Structures: Strings (Session). Hashes (User/Tenant metadata). Sets (Leaderboards). Streams (Events).
2. [REQ] Patterns: Cache-Aside (Default). Write-Through (Read-heavy config). Lua scripts for atomicity.
3. [REQ] Cluster: ElastiCache Cluster Mode. Eviction: `allkeys-lru` or `volatile-lru`.
4. [PROHIBIT] Constraints: NEVER `KEYS *` (use `SCAN`). NEVER cache unbounded collections. ALWAYS set a TTL.
