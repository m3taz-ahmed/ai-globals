# Tech-Stack: Redis 7

> [!NOTE]
> **TRIGGER:** LOAD ON caching implementation, rate limiting, session management, job queues.
> **SCOPE:** Redis 7 patterns, ElastiCache cluster mode integration.

## 1. Data Structures & Usage
- Use **Strings** for basic key-value caching (e.g., session state, serialized objects).
- Use **Hashes** for caching user profiles or tenant metadata to reduce memory overhead.
- Use **Sets / Sorted Sets** for leaderboards, unique visitor tracking, and tagging.
- Use **Streams** for event-driven architectures or logging when Kafka is overkill.

## 2. Caching Patterns
- Implement **Cache-Aside** as the default pattern: check cache -> if miss, fetch DB -> write to cache.
- Implement **Write-Through** caching for highly read-heavy, low-latency configuration data.
- Utilize Redis for centralized Session storage to support stateless backend nodes.
- Implement Rate Limiting using sliding window techniques via Lua scripting for atomicity.

## 3. Cluster & Optimization
- Deploy via AWS ElastiCache in Cluster Mode for high availability and sharding.
- Configure appropriate eviction policies (e.g., `allkeys-lru` or `volatile-lru`).
- Optimize memory usage by keeping keys short and using Hashes instead of multiple String keys.

## 4. Hard Constraints
- NEVER execute blocking commands like `KEYS *` in production (use `SCAN` instead).
- NEVER cache unbounded collections without pagination or limits.
- ALWAYS set a TTL (Time-To-Live) on cache keys unless they are explicitly managed configuration flags.

---

## ✅ REDIS 7 COMPLIANCE CHECK (Mandatory)
- [ ] **Safety:** Are `KEYS *` and other blocking commands strictly avoided?
- [ ] **Lifecycle:** Does every cache key have a deliberate TTL and eviction strategy?
- [ ] **Atomicity:** Are multi-step operations combined using Lua scripts or transactions?
