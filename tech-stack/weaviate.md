[TECH] Weaviate
[OBJ] Open-source vector-first search engine with GraphQL API, modular vectorization, multi-tenancy, hybrid search, and generative search capabilities.
[RULES]
1. [REQ] Use collections (v1.19+) instead of classes (v1.18-); collections are the schema unit with defined vectorizer, vector index type, and properties.
2. [REQ] Configure a vectorizer module (e.g., `text2vec-openai`, `text2vec-cohere`, `text2vec-transformers`) on the collection or provide custom vectors via `vector` parameter on batch import.
3. [REQ] Enable multi-tenancy with `multiTenancyConfig: {enabled: true}` on the collection; use `X-Tenant-ID` header on all requests to isolate tenant data per shard.
4. [REQ] Use hybrid search with `hybrid` query operator and an `alpha` parameter (0.0 = pure BM25 keyword, 1.0 = pure vector); tune alpha per dataset and query type.
5. [REQ] Set `vectorIndexConfig` with `vectorCacheMaxObjects` tuned to available RAM; uncached vectors require disk reads and increase p99 latency significantly.
6. [CMD] Batch import with `BATCH` GraphQL mutation or REST `/batch/objects` endpoint; batch size 100-200 objects for optimal throughput; use `consistency_level` of `ONE` for speed or `ALL` for correctness.
7. [REQ] Use `where` filters with operators (`Equal`, `GreaterThan`, `Like`, `ContainsAny`) for scalar property filtering; combine with `nearVector` or `hybrid` for filtered vector search.
8. [REQ] Enable `generative-search` module (e.g., `generative-openai`, `generative-cohere`) and use `generate` GraphQL argument for single-prompt or grouped RAG tasks at query time.
9. [REQ] Configure backups with `BACKUP` API to S3, GCS, Azure Blob, or filesystem; schedule regular backups for production clusters; test restore in a separate instance.
10. [REQ] Use HNSW as the default vector index (`vectorIndexType: "hnsw"`); use `flat` or `dynamic` for small datasets (<10K) where HNSW overhead is not justified.
11. [REQ] Set `distance` metric (`cosine`, `dot`, `l2-squared`, `hamming`, `manhattan`) on collection creation; this is immutable — changing it requires a new collection and re-import.
12. [REQ] Secure the cluster with authentication (`Authorization: Bearer <token>`) and RBAC (v1.25+); disable anonymous access in production via `AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=false`.
13. [REQ] Monitor `weaviate_objects_total`, `weaviate_hnsw_tombstones`, and shard health; tombstones accumulate from deletions and require compaction to reclaim disk space.
14. [PROHIBIT] Do not store raw embeddings alongside Weaviate-managed vectors; either let the vectorizer module compute vectors or pass explicit vectors — never both on the same object.
15. [PROHIBIT] Do not run multi-tenant collections without enabling multi-tenancy; without it, all tenant data shares the same shards and `X-Tenant-ID` headers are silently ignored.
[COMPAT]
- v1.25+: RBAC, named vectors, multi-vector references, backup improvements
- v1.22+: Hybrid search with BM25 + vector, generative search modules, multi-tenancy GA
- v1.19+: Collections API (replaces classes), gRPC batch import
- Deployment: Docker, Kubernetes (Helm), Weaviate Cloud (WCD), Embedded Weaviate (Python)
[REFS]
- https://weaviate.io/developers/weaviate
- https://weaviate.io/developers/weaviate/manage-collections
- https://weaviate.io/developers/weaviate/search/hybrid
- https://weaviate.io/developers/weaviate/manage-tenant-data
- https://weaviate.io/developers/weaviate/backup-restore
- https://weaviate.io/developers/weaviate/modules/generative
