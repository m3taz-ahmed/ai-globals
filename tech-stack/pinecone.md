[TECH] Pinecone
[OBJ] Serverless vector database for high-scale semantic search and RAG with managed indexing, namespaces, and hybrid search.
[RULES]
1. [REQ] Prefer Serverless index architecture over Pods for new projects; Serverless auto-scales storage and compute with pay-per-use pricing and no capacity planning.
2. [REQ] Use namespaces to partition a single index by tenant, user, or dataset; namespaces support independent upsert/delete and queries without separate indexes.
3. [REQ] Keep metadata values flat (strings, numbers, booleans, lists of strings); nested objects and null values are rejected on upsert.
4. [REQ] Limit metadata per vector to 40 KB; total vector dimension cap is 20,000 for dense and 96,000 for sparse vectors.
5. [REQ] Use sparse-dense vectors with `sparse_values` for hybrid search; combine lexical (BM25-style sparse) and semantic (dense) signals in a single query.
6. [CMD] Upsert in batches of 100 vectors max to stay within request size limits and avoid timeouts; use async upserts for large datasets.
7. [REQ] Use `top_k` values <= 1,000 for queries; higher values increase latency and cost without meaningful recall gains for most RAG workloads.
8. [REQ] Apply metadata filtering at query time with `$eq`, `$in`, `$gte`, `$lte`, `$and`, `$or` operators to narrow the search space before vector similarity.
9. [REQ] Use `namespace` parameter on every query and upsert; omitting it defaults to the empty-string namespace, causing cross-tenant data leakage in multi-tenant setups.
10. [REQ] Store API keys in environment variables or a secrets manager; never hardcode keys in application code or repository files.
11. [REQ] Use `include_metadata=true` and `include_values=false` in queries unless you need raw vectors back; returning values increases payload size and latency.
12. [REQ] Monitor `p99_latency` and `upsert_throttle` metrics; Serverless cold-start latency on first query after inactivity is expected and should be warmed for latency-sensitive apps.
13. [REQ] Use the `pinecone` Python/Node SDK with connection pooling; create one Pinecone client instance per process and reuse it across requests.
14. [PROHIBIT] Do not use Pods architecture for new serverless-eligible workloads unless you need fixed capacity, specific regions, or GPU acceleration not available in Serverless.
15. [PROHIBIT] Do not delete and recreate indexes to change dimension count or metric; index type and metric are immutable after creation — create a new index and migrate instead.
[COMPAT]
- v3.0+: Serverless indexes, sparse-dense hybrid search, namespace operations (Python/Node SDK v3+)
- v2.2+: Pods architecture, metadata filtering, collections (legacy)
- Regions: AWS (us-east-1, us-west-2, eu-west-1), GCP (us-central1, europe-west4), Azure (eastus2)
[REFS]
- https://docs.pinecone.io/guides/get-started/overview
- https://docs.pinecone.io/reference/api/overview
- https://docs.pinecone.io/guides/serverless/architecture
- https://docs.pinecone.io/guides/data/upsert-data
- https://docs.pinecone.io/guides/data/filter-with-metadata
- https://docs.pinecone.io/guides/data/hybrid-search
