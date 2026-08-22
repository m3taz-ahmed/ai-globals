[TECH] Apache Kafka
[OBJ] Distributed event streaming platform for high-throughput pub/sub messaging, stream processing, and event sourcing with partitioned topics and consumer groups.
[RULES]
1. [REQ] Choose partition count based on target throughput: each partition supports ~10MB/s; over-partitioning increases overhead, under-partitioning limits parallelism.
2. [REQ] Use a meaningful partition key (e.g., `orderId`, `userId`) to guarantee ordering within a partition; messages without keys use round-robin distribution.
3. [REQ] Configure consumer groups with `group.id` for parallel consumption; each partition is consumed by exactly one consumer per group.
4. [REQ] Use `enable.auto.commit=false` and commit offsets manually after processing; commit synchronously for critical data, asynchronously for high-throughput.
5. [REQ] Use idempotent producers (`enable.idempotence=true`) to prevent duplicate messages from retries; combine with transactions for exactly-once semantics.
6. [REQ] For exactly-once semantics (EOS), use the transactional API: `transactional.id`, `initTransactions()`, `beginTransaction()`, `commitTransaction()`; consumers must set `isolation.level=read_committed`.
7. [REQ] Set `acks=all` for producers to ensure durability; set `min.insync.replicas` >= 2 on topics with replication factor >= 3.
8. [REQ] Use Schema Registry (Confluent or Apicurio) with Avro/Protobuf/JSON Schema for contract management; register schemas before producing, use `AUTO_REGISTER_SCHEMAS=false` in production.
9. [REQ] Use Kafka Streams for stateful stream processing; use `Stores.persistentKeyValueStore()` for state stores with changelog topics for fault tolerance.
10. [REQ] Use KRaft mode (Kafka Raft metadata) instead of ZooKeeper for new deployments; KRaft eliminates the ZooKeeper dependency and simplifies operations.
11. [REQ] Configure retention by time (`retention.ms`) and/or size (`retention.bytes`); use `cleanup.policy=compact` for changelog topics to retain latest value per key.
12. [REQ] Monitor consumer lag via `kafka-consumer-groups --describe` or Burrow/Confluent Control Center; alert on lag exceeding SLA thresholds.
13. [REQ] Use `max.poll.records` and `max.poll.interval.ms` to prevent consumer rebalance storms; process batches within the poll interval to avoid being kicked out of the group.
14. [PROHIBIT] Never use `acks=0` or `acks=1` in production for critical data; data loss occurs on broker failure before replication completes.
15. [PROHIBIT] Never rely on message ordering across partitions; Kafka guarantees ordering only within a single partition.
[COMPAT]
- v3.8+: KRaft mode (no ZooKeeper), tiered storage, Kafka Streams, Kafka Connect, Schema Registry
- v3.8+: Clients: Java, Python (confluent-kafka, kafka-python), Go (sarama, segmentio/kafka-go), Node.js (kafkajs)
- v3.8+: Confluent Platform, Confluent Cloud, Apache Kafka (OSS), AWS MSK, Aiven
[REFS]
- https://kafka.apache.org/documentation/
- https://kafka.apache.org/documentation/#semantics
- https://docs.confluent.io/platform/current/schema-registry/
- https://kafka.apache.org/38/documentation/streams/
- https://kafka.apache.org/documentation/#kraft
