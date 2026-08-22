[TECH] Prometheus
[OBJ] Open-source metrics-based monitoring and alerting system with a multi-dimensional data model, PromQL query language, and pull-based scrape architecture.
[RULES]
1. [REQ] Use the four metric types correctly: Counter (monotonically increasing), Gauge (can go up/down), Histogram (bucketed distributions with `_bucket`, `_sum`, `_count`), Summary (quantiles client-side — prefer Histogram for aggregatable percentiles).
2. [REQ] Label metrics with high-cardinality dimensions carefully (namespace, pod, service) but never with user IDs, request paths with parameters, or trace IDs — these cause unbounded series explosion.
3. [REQ] Configure service discovery (static, Kubernetes SD, EC2 SD, file_sd) to dynamically discover scrape targets; avoid hardcoded `static_configs` in dynamic environments.
4. [REQ] Set `scrape_interval` (default 15s) and `scrape_timeout` (must be < scrape_interval) per job; use longer intervals (60s) for slow exporters to reduce load.
5. [REQ] Define alerting rules in `rules.yml` with `for:` duration to avoid flappy alerts; use `alert` and `record` rule groups with `limit` to control evaluation cost.
6. [REQ] Define recording rules for frequently computed PromQL expressions (e.g., `rate()` over high-cardinality metrics) to pre-aggregate and reduce query latency on dashboards.
7. [REQ] Use `relabel_configs` to filter, rename, or enrich target labels before scraping; use `metric_relabel_configs` to drop or rename metrics after scraping (e.g., drop `go_*` runtime metrics).
8. [REQ] Configure Alertmanager with routing trees (`route`, `receivers`, `group_by`, `group_wait`, `group_interval`, `repeat_interval`) to deduplicate and route alerts to the right on-call team.
9. [REQ] Use Thanos or Cortex/Mimir for long-term storage, high availability, and global query federation across multiple Prometheus instances.
10. [CMD] Use `promtool check config prometheus.yml` to validate configuration; use `promtool check rules rules.yml` to validate alerting and recording rules.
11. [CMD] Use `promtool tsdb query <expr>` for CLI PromQL queries; use `promtool debug all <url>` to capture debug bundles for support.
12. [CMD] Use `kubectl port-forward svc/prometheus 9090` for local UI access; use the HTTP API `/api/v1/query?query=<expr>` for programmatic queries.
13. [PROHIBIT] Never use `rate()` with a range smaller than 2x the scrape interval — it will produce gaps and NaN values; minimum range window is `2 * scrape_interval`.
14. [PROHIBIT] Never store secrets in Prometheus config — use `remote_write` with bearer token files or mTLS; never embed credentials in `scrape_configs` URLs.
15. [PROHIBIT] Never run a single Prometheus instance for production HA — use two instances with Alertmanager deduplication or Thanos/Mimir for HA + long-term storage.
[COMPAT]
- v2.52.x: UTF-8 metric/label names support (experimental), OTLP receiver improvements, native histograms (experimental)
- v2.54.x: Native histograms beta, `scrape_classic_histograms` flag, improved Kubernetes SD
- v3.0.x: Native histograms GA, UTF-8 names GA, OTLP ingestion GA, new PromQL functions
[REFS]
- https://prometheus.io/docs/
- https://prometheus.io/docs/prometheus/latest/querying/basics/
- https://prometheus.io/docs/prometheus/latest/configuration/configuration/
- https://thanos.io/
