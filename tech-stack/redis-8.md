[TECH] Redis 8.10
[OBJ] Redis 8.10.x (latest 8.10.1 Aug 2026). Major memory/perf improvements, XADD idempotency, LRM eviction, HOTKEYS command, TLS cert auth, time-series NaN support. Major release — review config + persistence.
[RULES]
1. [REQ] Review config + persistence behavior on upgrade to 8.x — major release with breaking changes to default configs, persistence semantics, and module compatibility. Test on staging replica first.
2. [REQ] Use `HOTKEYS` command to identify hot keys causing uneven memory/CPU: `HOTKEYS topkeys 10`. Monitor in production for skew detection.
3. [REQ] Use XADD idempotency: `XADD stream * field value` with explicit ID control. Duplicate detection via `XADD ... MAXLEN ~ N` for bounded streams.
4. [REQ] Use LRM (Least Recently Modified) eviction for workloads with write-skew: `maxmemory-policy allkeys-lru` or new `allkeys-lrm`. LRM evicts by modification time, not access time.
5. [REQ] Use TLS certificate authentication: `tls-cert-file`, `tls-key-file`, `tls-ca-cert-file` + `tls-auth-clients yes` for mTLS. Replaces password-only auth for zero-trust.
6. [REQ] Use Redis TimeSeries module with NaN support: `TS.CREATE key RETENTION 86400 LABELS ...`. Handle `NaN` in `TS.MRANGE` / `TS.RANGE` for missing data points.
7. [REQ] Use Redis Streams for event logging + consumer groups: `XADD`, `XREADGROUP GROUP group consumer`, `XACK`. At-least-once delivery with idempotent consumers.
8. [REQ] Use Redis Cluster for horizontal scaling (sharding). `redis-cli --cluster create` for setup. Use `MOVED` / `ASK` redirection handling in client.
9. [REQ] Use `EXPIRE` / `TTL` / `PERSIST` for key expiration. Use `SETEX` / `SET key value EX seconds` for atomic set+expire.
10. [REQ] Use `MULTI` / `EXEC` for transactions (optimistic locking with `WATCH`). Use Lua scripts (`EVAL`) for atomic multi-key operations.
11. [REQ] Use `Pub/Sub` (`PUBLISH` / `SUBSCRIBE`) for real-time notifications. For durability, use Streams (Pub/Sub is fire-and-forget).
12. [REQ] Use `redis-py` 5.0+ (Python) or `ioredis` 5.0+ (Node.js) with connection pooling. Use async clients (`redis.asyncio`, `ioredis`) in async apps.
13. [REQ] Use `SCAN` (cursor-based) for key iteration — never `KEYS *` in production (blocks server).
14. [REQ] Use `MEMORY USAGE key` for per-key memory analysis. `MEMORY STATS` for server-level. `INFO memory` for overview.
15. [REQ] Enable AOF persistence (`appendonly yes`, `appendfsync everysec`) for durability. RDB snapshots for backups. Combine AOF + RDB for best of both.
16. [REQ] Use `redis-sentinel` for HA (automatic failover) or Redis Cluster for sharding + HA. Never single-instance in production.
17. [CMD] `redis-cli HOTKEYS topkeys 10` identify hot keys.
18. [CMD] `redis-cli --tls --cert client.crt --key client.key --cacert ca.crt` connect with mTLS.
19. [CMD] `redis-benchmark -t set,get -n 100000 -q` benchmark performance.
20. [PROHIBIT] Never use `KEYS *` in production — use `SCAN` with cursor.
21. [PROHIBIT] Never use `FLUSHALL` / `FLUSHDB` in production without explicit approval.
22. [PROHIBIT] Never store large values (>100KB) in Redis — use object storage (S3) + Redis for metadata/pointers.
23. [PROHIBIT] Never use `SELECT` (multi-DB) in Redis Cluster (single DB only).
[COMPAT]
- Redis 8.10.x (latest 8.10.1 Aug 2026).
- Major release — review upgrade guide for config/persistence changes.
- Modules: RedisTimeSeries 1.12+, RedisJSON 2.8+, RediSearch 2.10+.
- Clients: redis-py 5.0+, ioredis 5.0+, node-redis 4.6+, go-redis 9.5+.
- TLS: mTLS cert auth supported natively.
[REFS]
- https://redis.io/docs/latest/
- https://redis.io/blog/redis-8/
- https://redis.io/commands/hotkeys/
- https://github.com/redis/redis
