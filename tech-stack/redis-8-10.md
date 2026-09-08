[TECH] Redis 8.10 (latest 8.10.1, Aug 2026)
[OBJ] Redis 8.10.x — compact hashes + `HIMPORT`, `BACKUP` command (multi-part AOF), `LMOVEM`/`BLMOVEM`, `SUNIONCARD`/`SDIFFCARD`, `XREAD`/`XREADGROUP` `MAXCOUNT`/`MAXSIZE`, new Time Series commands (`TS.NRANGE`, `TS.READ`, `TS.QUERYLABELS`), hash templates, `FT.AGGREGATE` `COLLECT` reducer.
[RULES]
1. [REQ] Use compact hashes + `HIMPORT` for bulk hash import — memory-efficient hash storage with bulk loading.
2. [REQ] Use `BACKUP` command (multi-part AOF) — online backup without blocking. Replaces `SAVE`/`BGSAVE` for production.
3. [REQ] Use `LMOVEM`/`BLMOVEM` — move multiple elements between lists atomically.
4. [REQ] Use `SUNIONCARD`/`SDIFFCARD` — cardinality of union/difference without materializing the set.
5. [REQ] Use `XREAD`/`XREADGROUP` with `MAXCOUNT`/`MAXSIZE` — bounded stream reads for memory safety.
6. [REQ] Use Time Series commands: `TS.NRANGE`, `TS.READ`, `TS.QUERYLABELS` — enhanced time-series querying.
7. [REQ] Use hash templates for consistent hash field structures — `HT.TEMPLATE` for schema enforcement.
8. [REQ] Use `FT.AGGREGATE` `COLLECT` reducer — custom aggregation in RediSearch.
9. [REQ] Use `HOTKEYS` command to identify hot keys: `HOTKEYS topkeys 10`.
10. [REQ] Use LRM (Least Recently Modified) eviction for write-skew workloads.
11. [REQ] Use TLS certificate authentication for mTLS: `tls-cert-file`, `tls-key-file`, `tls-ca-cert-file`.
12. [REQ] Use Redis Streams for event logging + consumer groups: `XADD`, `XREADGROUP`, `XACK`.
13. [PROHIBIT] Never use `SAVE` in production (blocks) — use `BACKUP` or `BGSAVE`.
14. [PROHIBIT] Never use password-only auth for zero-trust — use TLS cert auth.
[COMPAT]
- Redis 8.10.1 (released Aug 17 2026).
- 8.10.0 GA (Jul 29 2026).
- Tested on Ubuntu 22.04/24.04/26.04, Rocky 8.10/9.7/10.1, Debian 12/13, macOS 14/15.
[REFS]
- https://redis.io/docs/latest/develop/whats-new/8-10/
- https://github.com/redis/redis/releases/tag/8.10.1
- https://redis.io/docs/
