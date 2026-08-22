[TECH] Grafana
[OBJ] Open-source observability and visualization platform for querying, correlating, and alerting on metrics, logs, and traces from multiple data sources.
[RULES]
1. [REQ] Configure data sources (Prometheus, Loki, Tempo, Elasticsearch, etc.) via provisioning YAML in `provisioning/datasources/` — not manual UI configuration.
2. [REQ] Provision dashboards as JSON in `provisioning/dashboards/` with a provider config YAML; version-control all dashboard definitions in Git.
3. [REQ] Use templating variables with `$variable` syntax for dynamic dashboards; bind queries to datasource, namespace, or pod selectors.
4. [REQ] Define alerting rules using Grafana Alerting (unified alerting) with `alert.rules` in provisioning or via AlertRule CRD; route notifications to Contact Points (Slack, PagerDuty, email).
5. [REQ] Set dashboard time range defaults and refresh intervals explicitly; avoid `now-1h` without a panel-level override for long-range capacity planning views.
6. [REQ] Use Grafana Loki for log aggregation with LogQL queries; correlate logs with traces via `traceID` extraction and Tempo data source linking.
7. [REQ] Use Grafana Tempo for distributed tracing with TraceQL queries; link traces to logs via service name and span attributes.
8. [REQ] Enable Grafana RBAC with role-based access (Admin, Editor, Viewer); integrate SSO via OAuth (GitHub, Google, Okta) or LDAP/SSO/SAML.
9. [REQ] Enable HTTPS with valid TLS certificates; set `force_https = true` in `grafana.ini` and `strict_transport_security` headers.
10. [CMD] Use `grafana-cli admin reset-admin-password` for password recovery; use `grafana-cli plugins install <plugin>` for panel/data source plugins.
11. [CMD] Use `grafana-cli admin ldap-sync` to synchronize LDAP users and groups after configuration changes.
12. [CMD] Use Grafana Cloud for managed Loki, Tempo, Mimir, and Grafana — reduces operational overhead for teams without dedicated observability SREs.
13. [PROHIBIT] Never expose Grafana without authentication — disable anonymous access (`allow_anonymous = false`) in production.
14. [PROHIBIT] Never store data source credentials in plaintext in provisioning YAML — use Grafana secret key encryption or environment variable references (`$__env{VAR}`).
15. [PROHIBIT] Never create dashboards manually in production without exporting to JSON and committing to Git — manual dashboards are lost on redeployment.
[COMPAT]
- v10.4.x: Unified alerting GA, scenes-based dashboards, Prometheus exemplar support
- v11.0.x: Grafana Loki 3.0 query frontend, new panel React components, alerting improvements
- v11.1.x: Tempo TraceQL improvements, Grafana OnCall integration GA
[REFS]
- https://grafana.com/docs/grafana/latest/
- https://grafana.com/docs/grafana/latest/administration/provisioning/
- https://grafana.com/docs/loki/latest/
- https://grafana.com/docs/tempo/latest/
