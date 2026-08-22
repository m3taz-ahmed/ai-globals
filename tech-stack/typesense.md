[TECH] Typesense
[OBJ] Open-source typo-tolerant search engine with instant search, geo search, vector search, multi-tenancy, curations, and synonyms — self-hosted or Typesense Cloud.
[RULES]
1. [REQ] Define a schema with `fields` array specifying `name`, `type` (`string`, `int32`, `float`, `bool`, `string[]`, `geopoint`, `float[]` for vectors), and `facet` flag; schema is immutable after creation except for adding new optional fields.
2. [REQ] Enable typo-tolerance with `typo_tolerance_enabled: true` in collection schema or per-query `query_by` with `num_typos` parameter (0, 1, or 2); prefix search is controlled by `prefix` parameter.
3. [REQ] Use `query_by` with comma-separated field names for multi-field search; field priority follows the order listed — first field has highest weight in relevance scoring.
4. [REQ] For vector search, define a `float[]` field with `num_dim` in schema and use `vector_query` parameter: `embedding:([0.1, 0.2, ...], k:100)`; combine with text search via `query_by` for hybrid search.
5. [REQ] Use multi-tenancy with `token` header containing a scoped API key generated from the parent key with `embed` payload restricting `search` to specific collections or filters; never expose the master API key to the client.
6. [CMD] Use the `/collections/:collection/documents` endpoint with `action: upsert` for idempotent inserts; use `action: create` to fail on duplicate IDs; batch up to 4096 documents per request.
7. [REQ] Use `filter_by` with operators (`:=`, `:`, `:[...],`, `:>`, `:<`, `:[..]`) for faceted filtering; combine multiple filters with `&&` (AND) and `||` (OR) logic.
8. [REQ] Configure curations via `/collections/:collection/overrides` to pin specific documents to the top or exclude them for given query patterns; use for merchandising and editorial control.
9. [REQ] Define synonyms via `/collections/:collection/synonyms` with `synonyms` array or one-way `root` → `synonyms` mapping; use for domain-specific vocabulary and common misspellings.
10. [REQ] Use `sort_by` with field and order (`price:asc`, `_text_match:desc`, `_geopoint(lat,lng):asc`); combine multiple sort criteria with comma separation — first criterion is primary.
11. [REQ] Use `facet_by` with comma-separated fields to return facet counts in search results; set `max_facet_values` to control the number of facet values returned per field.
12. [REQ] Enable geo search with `geopoint` field type and `filter_by: location(48.8566, 2.3522, 50 km)` syntax; use `_geopoint(lat, lng)` in `sort_by` for distance-based ordering.
13. [REQ] Secure the deployment with API key auth; use scoped search-only keys for frontend clients; enable CORS with allowed origins in `typesense-server` config; never expose write keys to the browser.
14. [REQ] Configure `num_cpu` and memory limits in `typesense-server` config; Typesense is RAM-heavy (all data in memory) — size instances based on total collection size, not just document count.
15. [PROHIBIT] Do not use the master API key in client-side code; generate scoped search keys with `typesense.Key` or the `/keys` endpoint with minimal permissions for frontend applications.
[COMPAT]
- v0.27.0+: Vector search (hybrid), multi-tenancy improvements, conversation history
- v0.25.0+: Vector search support, `float[]` field type, semantic search
- v0.24.0+: Curations, synonyms, geo search, facet query improvements
- Deployment: Docker, Kubernetes, Typesense Cloud (managed), bare metal
[REFS]
- https://typesense.org/docs/
- https://typesense.org/docs/guide/
- https://typesense.org/docs/api/
- https://typesense.org/docs/guide/vector-search.html
- https://typesense.org/docs/guide/typo-tolerance.html
- https://typesense.org/docs/guide/multi-tenant-search.html
