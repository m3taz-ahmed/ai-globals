[TECH] mysql-8-3
[OBJ] MySQL 8.3 Architecture Standards.
[RULES]
1. [REQ] Replication: GTID-based replication. InnoDB Cluster with Group Replication.
2. [REQ] JSON: Multi-valued indexes (`CAST(... AS UNSIGNED ARRAY)`). `JSON_TABLE()`. ⛔ NO bypassing normalization with JSON.
3. [REQ] Queries: Use CTEs and Window Functions (`ROW_NUMBER()`). Optimize with `EXPLAIN ANALYZE`.
4. [REQ] InnoDB: `innodb_buffer_pool_size` 70-80% RAM. Partition pruning (>10M rows). Invisible indexes for testing.
