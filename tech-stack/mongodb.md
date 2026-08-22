[TECH] MongoDB
[OBJ] Document-oriented NoSQL database with flexible schema, aggregation pipeline, horizontal scaling via sharding, and replica sets for high availability.
[RULES]
1. [REQ] Design documents around access patterns; embed sub-documents for frequently-read-together data, reference (ObjectId) for large or independently-updated data.
2. [REQ] Create indexes for every query field used in `find()`, `sort()`, and `match` stages; use `createIndex()` with `background: true` in production to avoid blocking writes.
3. [REQ] Use compound indexes following the ESR (Equality, Sort, Range) rule; place equality fields first, sort fields second, range fields last.
4. [REQ] Use the aggregation pipeline (`aggregate()`) for complex transformations; chain `$match` early to reduce document flow and leverage indexes.
5. [REQ] Use `explain("executionStats")` to verify index usage and `totalDocsExamined` vs `nReturned` ratio; investigate if ratio exceeds 10:1.
6. [REQ] Use transactions (`session.withTransaction()`) for multi-document atomicity on replica sets; keep transactions short (<60s) to avoid abort on timeout.
7. [REQ] Configure replica sets with minimum 3 members (1 primary + 2 secondaries) for production; use arbiter only in cost-constrained non-critical deployments.
8. [REQ] Use change streams (`collection.watch()`) for real-time event-driven architectures; start from `resumeToken` to ensure at-least-once delivery after restarts.
9. [REQ] For sharding, choose a shard key with high cardinality, low frequency, and non-monotonic distribution to prevent hot shards; shard key is immutable after collection creation.
10. [REQ] Use Atlas for managed deployments; configure VPC peering, private endpoints, and IP access lists for production security.
11. [REQ] Use `readPreference` strategically: `secondary` for analytics/reporting, `primary` for strong consistency, `nearest` for geo-distributed low-latency reads.
12. [REQ] Enable field-level encryption (CSFLE) for PII; store master keys in a KMS (AWS KMS, Azure Key Vault, GCP KMS), never in application code.
13. [REQ] Use `$jsonSchema` validator in `collection.createCollection()` to enforce document structure; use `validationLevel: 'strict'` for new collections.
14. [PROHIBIT] Never use `eval` or `$where` with user input; they execute JavaScript on the server and enable injection attacks.
15. [PROHIBIT] Never create unbounded arrays in documents (document size limit 16MB); use referencing for unbounded one-to-many relationships.
[COMPAT]
- v7.x: WiredTiger storage engine, time series collections, Atlas Search (Lucene), Atlas Vector Search
- v7.x: MongoDB Atlas (M0-M80 tiers), Atlas App Services, Atlas Device Sync
- v7.x: Drivers: Node.js (mongodb), Python (pymongo), Go (mongo-go-driver), Java, .NET
[REFS]
- https://www.mongodb.com/docs/manual/
- https://www.mongodb.com/docs/manual/core/aggregation-pipeline/
- https://www.mongodb.com/docs/manual/core/transactions/
- https://www.mongodb.com/docs/manual/core/change-streams/
- https://www.mongodb.com/docs/atlas/
- https://www.mongodb.com/docs/manual/core/sharding-shard-key/
