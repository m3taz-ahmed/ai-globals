---
name: database-internals-example
---
[FILE] database-internals-example
[OBJ] Compressed reference card for database internals derived from cmu-db/bustub, cstack/db_tutorial, facebook/rocksdb, redis/redis, duckdb/duckdb.
[CONTEXT] Use when reasoning about storage engines, query execution, or performance optimization.
[RULES]
1. [STORAGE] Row stores (B+Tree, heap) for OLTP; column stores / vectorized execution for OLAP; LSM trees for high write throughput.
2. [BUFFER] Buffer pool caches pages; eviction policy matters. Pin pages during access; write WAL before dirty page flush.
3. [WAL] Write-ahead log provides durability and crash recovery; LSNs order transactions and enable point-in-time recovery.
4. [MVCC] Multi-version concurrency control avoids writer-reader blocking; each transaction sees a consistent snapshot.
5. [EXECUTION] Parser -> binder -> planner -> optimizer -> executor. Cost model uses selectivity, cardinality, index availability.
6. [INDEX] B+Trees for range scans, hash for point lookups, inverted for full-text, HNSW/IVF for vector search.
7. [QUERY] DuckDB for in-process analytics; Redis for hot data structures; RocksDB for embeddable KV; SQLite for embedded SQL; BusTub for learning the stack end-to-end.
8. [REFERENCES] `cmu-db/bustub` (educational RDBMS), `cstack/db_tutorial` (build SQLite from scratch), `facebook/rocksdb`, `redis/redis`, `duckdb/duckdb`.
