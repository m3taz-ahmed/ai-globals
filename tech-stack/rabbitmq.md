[TECH] RabbitMQ
[OBJ] Multi-protocol message broker implementing AMQP 0-9-1 with exchanges, queues, bindings, and flexible routing for reliable message delivery.
[RULES]
1. [REQ] Use direct exchanges for routing-key-based unicast, topic exchanges for pattern-based routing (`*` and `#` wildcards), fanout exchanges for broadcast, and headers exchanges for attribute-based routing.
2. [REQ] Declare queues as durable (`durable: true`) for persistent messages that survive broker restarts; use `persistent: true` on message delivery mode for disk-backed storage.
3. [REQ] Set `prefetch_count` (QoS) per consumer to control fair dispatch; start with 10-50 and tune based on processing latency and consumer capacity.
4. [REQ] Use manual acknowledgement (`autoAck: false`); ack only after successful processing, nack with `requeue: false` for poison messages to dead-letter exchange (DLX).
5. [REQ] Configure dead-letter exchanges (`x-dead-letter-exchange`) and dead-letter queues for failed messages; set `x-dead-letter-routing-key` for explicit DLQ routing.
6. [REQ] Use `x-max-retries` or TTL + DLX pattern for retry with backoff; do not requeue infinitely as it causes message storms.
7. [REQ] Use priority queues (`x-max-priority`) when message urgency varies; set `x-max-priority` on queue declaration and `priority` on message properties.
8. [REQ] Use channels for per-connection multiplexing; open one channel per thread/consumer, never share channels across threads.
9. [REQ] Use publisher confirms (`confirm.select()`) for reliable publishing; wait for `ack`/`nack` to ensure the broker accepted the message.
10. [REQ] Use RabbitMQ Streams (single-active consumer, append-only log) for high-throughput fanout scenarios (>100K msg/s) where AMQP queues are insufficient.
11. [REQ] Use the MQTT plugin (`rabbitmq_mqtt`) for IoT device connectivity; configure TLS (8883) and map MQTT topics to AMQP exchanges via `mqtt.exchange` setting.
12. [REQ] Enable TLS for all connections; configure `ssl_options` with certificate verification and use `fail_if_no_peer_cert: true` for mutual TLS in production.
13. [REQ] Use mirrored queues (classic) or quorum queues (recommended) for high availability; quorum queues use Raft consensus and survive node failures without data loss.
14. [PROHIBIT] Never use `autoAck: true` in production for critical workloads; messages are acknowledged on delivery and lost if processing fails.
15. [PROHIBIT] Never create unbounded queues without TTL or max-length limits (`x-message-ttl`, `x-max-length`); unbounded queues cause memory exhaustion and broker crashes.
[COMPAT]
- v3.13+/4.0: AMQP 0-9-1, AMQP 1.0, MQTT 3.1.1/5.0, STOMP, Streams
- v4.0: Quorum queues, streams (RabbitMQ Stream protocol), Khepri (alternative metadata store)
- v4.0: Clients: Java, Python (pika, aio-pika), Go (amqp091-go, rabbitmq/amqp091-go), Node.js (amqplib), .NET
[REFS]
- https://www.rabbitmq.com/docs
- https://www.rabbitmq.com/docs/quorum-queues
- https://www.rabbitmq.com/docs/streams
- https://www.rabbitmq.com/docs/dlx
- https://www.rabbitmq.com/docs/mqtt
