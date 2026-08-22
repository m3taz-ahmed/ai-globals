[TECH] Apache Cassandra
[OBJ] Distributed wide-column NoSQL database optimized for high-throughput writes, linear scalability, and multi-region availability with tunable consistency.
[RULES]
1. [REQ] Design tables around queries (query-first modeling); each table serves a specific access pattern, and denormalization is expected and encouraged.
2. [REQ] Define partition keys to distribute data evenly across nodes; use composite partition keys (`PARTITION KEY (a, b)`) for high-cardinality distribution.
3. [REQ] Use clustering keys (`CLUSTERING ORDER BY`) to sort rows within a partition; clustering columns support range queries and `ORDER BY` within the partition.
4. [REQ] Avoid unbounded partition growth; partitions should stay under 100MB and fewer than 100K rows for optimal performance.
5. [REQ] Choose consistency levels per query: `ONE`/`LOCAL_ONE` for maximum availability, `QUORUM`/`LOCAL_QUORUM` for strong consistency, `ALL` only when every node must acknowledge.
6. [REQ] Use `LOCAL_QUORUM` in multi-region deployments to avoid cross-region latency; `QUORUM` requires quorum across all datacenters.
7. [REQ] Use lightweight transactions (`IF NOT EXISTS`, `IF condition`) for compare-and-set operations only when necessary; they use Paxos and incur 4x latency overhead.
8. [REQ] Configure compaction strategy per workload: `SizeTieredCompactionStrategy` (STCS) for write-heavy, `LeveledCompactionStrategy` (LCS) for read-heavy, `TimeWindowCompactionStrategy` (TWCS) for time-series data.
9. [REQ] Use materialized views (`CREATE MATERIALIZED VIEW`) sparingly; they add write amplification and have consistency limitations; prefer denormalized base tables.
10. [REQ] Use counters (`counter` type) only for distributed counters; they are not idempotent and cannot be mixed with non-counter columns in the same table.
11. [REQ] Set appropriate TTL on time-series data (`USING TTL`) for automatic expiration; pair with TWCS for efficient compaction of expired data.
12. [REQ] Configure replication factor per keyspace (`replication = {'class': 'NetworkTopologyStrategy', 'dc1': 3}`); use `NetworkTopologyStrategy` for multi-region, never `SimpleStrategy` in production.
13. [REQ] Run `nodetool repair` regularly (every `gc_grace_seconds`, default 10 days) to prevent deleted data resurrection from hinted handoff.
14. [PROHIBIT] Never use `ALLOW FILTERING` in production queries; it scans entire partitions and causes severe performance degradation.
15. [PROHIBIT] Never use `IN` on partition keys; it creates multiple uncoordinated queries and bypasses partition pruning.
[COMPAT]
- v5.x: CQL (Cassandra Query Language), virtual tables, SASI indexes
- v5.x: ScyllaDB (C++ rewrite, compatible CQL, 5-10x throughput), ScyllaDB Enterprise
- v5.x: Drivers: Java, Python (cassandra-driver), Go (gocql), Node.js (cassandra-driver), C++
[REFS]
- https://cassandra.apache.org/doc/latest/
- https://cassandra.apache.org/doc/latest/cql/
- https://cassandra.apache.org/doc/latest/architecture/
- https://www.scylladb.com/
- https://cassandra.apache.org/doc/latest/operating/compaction/
