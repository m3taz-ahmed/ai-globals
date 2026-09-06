[TECH] MySQL 26.7 (Jul 2026)
[OBJ] MySQL database — calendar versioning (YY.M.P), Change Stream Applier, post-quantum TLS 1.3, Thread Pool plugin to Community. Innovation release (short support).
[RULES]
1. [REQ] Calendar versioning: YY.M.P format (26.7 = year 2026, month 7, patch). Version numbers are NOT semver — do not treat minor bumps as backward-compatible.
2. [REQ] Innovation release = short support lifecycle. For production, use 9.7.2 LTS instead of 26.x innovation releases.
3. [REQ] Use Change Stream Applier for CDC (change data capture) — replaces legacy binlog parsing for replication/streaming use cases.
4. [REQ] Post-quantum TLS 1.3 enabled by default — ensure client drivers support PQ TLS 1.3 or configure fallback.
5. [REQ] Thread Pool plugin now in Community Edition — enable via `thread_pool_size`, `thread_pool_stall_limit` in `my.cnf`.
6. [REQ] Use `InnoDB` as default engine — never use `MyISAM` for new tables.
7. [REQ] Use parameterized queries / prepared statements — never interpolate SQL strings.
8. [REQ] Use `utf8mb4` charset + `utf8mb4_0900_ai_ci` collation for all new tables.
9. [REQ] Use foreign keys with `ON DELETE` / `ON UPDATE` constraints explicitly defined.
10. [REQ] Use `EXPLAIN ANALYZE` for query optimization — review execution plans before deploying queries.
11. [REQ] Use `mysqldump` or `mysqlpump` or MySQL Shell backup for backups; test restore regularly.
12. [REQ] Enable `innodb_buffer_pool_size` = 50-70% of available RAM for OLTP workloads.
13. [PROHIBIT] Never use MySQL 26.x innovation releases in production — use 9.7.2 LTS.
14. [PROHIBIT] Never use `MyISAM` for new tables — use `InnoDB`.
15. [PROHIBIT] Never use `utf8` (3-byte) charset — use `utf8mb4`.
16. [PROHIBIT] Never interpolate SQL strings — use prepared statements.
17. [PROHIBIT] Never disable TLS in production — post-quantum TLS 1.3 is default.
18. [CMD] `mysql -u root -p` — connect.
19. [CMD] `mysqld --initialize-insecure` — initialize data directory.
20. [CMD] `mysqlsh` — MySQL Shell (admin/backup/replication).
[COMPAT]
- MySQL 26.7: innovation release, short support.
- Production: use 9.7.2 LTS.
- Post-quantum TLS 1.3 default — client drivers must support.
- Thread Pool plugin: now Community Edition.
- Change Stream Applier: new CDC mechanism.
- Calendar versioning: YY.M.P (not semver).
[REFS]
- https://dev.mysql.com/doc/
- https://dev.mysql.com/doc/relnotes/mysql/26.7/
- https://dev.mysql.com/doc/refman/9.7/en/ (LTS)
