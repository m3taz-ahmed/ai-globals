# MySQL 8.3 Architecture Standards

## 1. REPLICATION & HIGH AVAILABILITY
- **GTID:** Utilize GTID-based replication enhancements for read-replicas. All transactions must be GTID-compatible.
- **Group Replication:** Prefer InnoDB Cluster with Group Replication for automatic failover in production.

## 2. JSON & DOCUMENT STORE
- **Multi-Valued Indexes:** Optimize JSON array extracts using multi-valued indexes (`CAST(data->'$.tags' AS UNSIGNED ARRAY)`).
- **JSON_TABLE:** Use `JSON_TABLE()` to convert JSON arrays into relational result sets for complex reporting.
- **Avoid Over-Use:** JSON columns are for dynamic/unstructured data only. Never use JSON to bypass proper relational normalization.

## 3. QUERY PERFORMANCE
- **CTEs:** Use Common Table Expressions for recursive queries and complex subquery chains. CTEs improve readability and are optimized in MySQL 8.x.
- **Window Functions:** Leverage `ROW_NUMBER()`, `RANK()`, `LAG()`, `LEAD()` for analytical queries instead of self-joins.
- **EXPLAIN ANALYZE:** Use `EXPLAIN ANALYZE` (not just `EXPLAIN`) to get actual execution times and row counts for query optimization.

## 4. INNODB OPTIMIZATIONS
- **Buffer Pool:** Size `innodb_buffer_pool_size` to ~70-80% of available RAM on dedicated database servers.
- **Partition Pruning:** Use RANGE or LIST partitioning for large tables (>10M rows) with time-based queries. Verify partition pruning with `EXPLAIN`.
- **Invisible Indexes:** Use invisible indexes (`ALTER TABLE ... ALTER INDEX idx INVISIBLE`) to test index removal impact without dropping.