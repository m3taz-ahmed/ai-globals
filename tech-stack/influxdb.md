[TECH] InfluxDB 3
[OBJ] Time-series database optimized for high-write-throughput telemetry with SQL/Flight query support, downsampling, and Telegraf ingestion.
[RULES]
1. [REQ] Write data using the line protocol (`measurement,tag_set field_set timestamp`); tags are indexed, fields are not; place high-cardinality data in fields, low-cardinality in tags.
2. [REQ] Use tags for filtering and grouping; every tag combination creates a series index — avoid high-cardinality tags (e.g., user IDs, UUIDs) to prevent series explosion.
3. [REQ] Use SQL queries (`SELECT ... FROM measurement WHERE time >= ...`) for InfluxDB 3 Core/Enterprise; Flight SQL and Arrow Flight protocols for high-performance columnar reads.
4. [REQ] Use buckets (InfluxDB Cloud) or databases (InfluxDB 3 Core) as the top-level namespace for time-series data; organize by retention policy and data source.
5. [REQ] Configure Telegraf as the ingestion agent; use `[[inputs.*]]` plugins for source-specific collection and `[[outputs.influxdb_v2]]` for InfluxDB 2.x or `[[outputs.influxdb]]` for 3.x.
6. [REQ] Implement downsampling via tasks (InfluxDB Cloud) or scheduled queries (InfluxDB 3); aggregate raw data into coarser granularities and set shorter retention on raw buckets.
7. [REQ] Set retention policies per bucket/database; keep raw data for short windows (e.g., 7 days), downsampled data for longer windows (e.g., 1 year).
8. [REQ] Use batch writes (5,000-10,000 points per batch) with the `write` API; flush every 1-5 seconds to balance latency and throughput.
9. [REQ] Use the `last()` function or `SELECT LAST(field) FROM measurement` for latest-value queries instead of scanning the full time range.
10. [REQ] Use Parquet file exports for cold storage and offline analysis; InfluxDB 3 stores data in Apache Arrow Parquet format natively.
11. [REQ] Handle write errors with retry logic and exponential backoff; check for `429 Too Many Requests` rate limiting in InfluxDB Cloud.
12. [REQ] Use InfluxDB Cloud for managed serverless deployments; choose AWS, Azure, or GCP regions closest to data sources to minimize write latency.
13. [REQ] Use the v2 client libraries (`influxdb-client-go`, `influxdb-client-python`, `influxdb-client-js`) with token-based authentication; never expose tokens in client-side code.
14. [PROHIBIT] Never use high-cardinality values as tags (e.g., timestamps, session IDs, UUIDs); each unique tag value creates a new series and degrades query performance.
15. [PROHIBIT] Never store discrete event data or relational data in InfluxDB; it is optimized for time-series, not OLTP workloads.
[COMPAT]
- v3.x: InfluxDB 3 Core (open source), InfluxDB 3 Enterprise, Apache Arrow columnar format, SQL + FlightSQL
- v2.x: InfluxDB Cloud (serverless), Flux query language, tasks, buckets, Telegraf
- v3.x: Clients: Python, Go, JavaScript, Java; Telegraf 1.30+
[REFS]
- https://docs.influxdata.com/influxdb3/
- https://docs.influxdata.com/influxdb3/core/
- https://docs.influxdata.com/telegraf/
- https://docs.influxdata.com/influxdb/cloud/
- https://docs.influxdata.com/influxdb3/core/reference/syntax/line-protocol/
