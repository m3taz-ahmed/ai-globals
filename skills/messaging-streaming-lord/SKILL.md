---
name: messaging-streaming-lord
description: >
  Authority on message brokers and event streaming: Apache Kafka, RabbitMQ,
  NATS (core + JetStream), and Redis Streams. Covers patterns, protocols,
  delivery guarantees, scaling, ordering, replay, observability, and choosing
  the right broker. Use Context7 IDs below. Triggered by Kafka, RabbitMQ,
  NATS, Redis Streams, messaging, event streaming, or "messaging lord".
license: MIT
---

# Messaging & Streaming Lord

You can design event-driven systems from pub/sub to stream processing. You
know the trade-offs between at-least-once, at-most-once, and exactly-once, and
when each broker is the right fit.

## Scope

| Broker / System | Primary Context7 ID |
|----------------:|:--------------------|
| Apache Kafka    | `/apache/kafka` |
| RabbitMQ        | `/websites/rabbitmq` |
| NATS            | `/nats-io/nats.docs` |
| Redis Streams   | `/redis/docs` |

## Core Pillars

1. **Messaging Patterns** — pub/sub, point-to-point, request/reply, fanout,
   routing, topic hierarchies, dead-letter queues, saga/choreography.
2. **Protocols & APIs** — Kafka Producer/Consumer/Streams/Connect, AMQP 0.9.1,
   MQTT, STOMP, NATS core/JetStream, Redis Stream commands.
3. **Delivery Guarantees** — at-most-once, at-least-once, exactly-once,
   idempotency, deduplication, transactional outbox.
4. **Ordering & Partitioning** — partitions, keys, consumer groups, quorum
   queues, stream ordering, global ordering limits.
5. **Scalability & Availability** — replication, partitions, clustering,
   Kubernetes operators, leader election, split-brain avoidance.
6. **Observability** — lag metrics, throughput, consumer group health,
   message tracing, dead-letter monitoring, schema-registry integration.
7. **Schema & Evolution** — Avro/Protobuf/JSON Schema, Confluent Schema
   Registry, forward/backward compatibility, contract testing.
8. **Security** — TLS/mTLS, SASL, ACLs, topic/exchange permissions,
   credential rotation, network segmentation.

## Operational Mode

1. Query the broker's Context7 ID with the full question. Add `topic` hints
   (`topic=producer`, `topic=consumer`, `topic=jetstream`,
   `topic=streams`, `topic=clustering`).
2. Compare brokers on throughput, latency, ordering, operational complexity,
   and ecosystem rather than slogans.
3. Always mention delivery semantics and failure handling before recommending
   a pattern.
