[TECH] postgresql-17
[OBJ] PostgreSQL 17 Deployment & Standards.
[RULES]
1. [REQ] Modeling: `JSONB` for schema-less. Table Partitioning for time-series. `UUIDv7` or `ULID` primary keys.
2. [REQ] Indexes: Partial Indexes for highly filtered queries. BRIN Indexes for time-series. GIN/GiST for `JSONB`/FTS.
3. [REQ] Queries: CTEs for hierarchies. Window Functions (`ROW_NUMBER()`).
4. [REQ] Ops: `shared_buffers` 25% RAM. PgBouncer/RDS Proxy.
5. [PROHIBIT] Constraints: NEVER run unbounded queries. NEVER `SELECT *`. ALWAYS `EXPLAIN ANALYZE`.
