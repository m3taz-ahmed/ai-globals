[TECH] Milvus
[OBJ] Distributed open-source vector database built on cloud-native architecture with collections, partitions, multiple index types, and scalar filtering.
[RULES]
1. [REQ] Use Milvus 2.x distributed mode (query nodes, data nodes, index nodes) for production; standalone mode is for development and testing only.
2. [REQ] Create collections with an explicit schema defining primary key, vector field (with `dim`), and scalar fields; set `auto_id=True` only if you do not manage IDs externally.
3. [REQ] Choose index type by dataset size and latency budget: IVF_FLAT (small/medium, exact), IVF_SQ8 (medium, quantized), HNSW (low latency, high memory), DiskANN (large-scale, disk-based, memory-efficient).
4. [REQ] Set `nlist` for IVF indexes during creation and `nprobe` at query time; `nprobe` < `nlist` trades recall for speed — tune empirically on your dataset.
5. [REQ] For HNSW, set `M` (16-64) and `efConstruction` (200-500) at index creation; set `ef` at query time >= `top_k` and <= `efConstruction` for recall control.
6. [CMD] Use partitions (`create_partition`) to segment data by category, tenant, or time window; query with `partition_names` to scan only relevant partitions and reduce latency.
7. [REQ] Use `expr` parameter for scalar field filtering with boolean expressions (`field > 10`, `field in [1,2,3]`, `field == "value"`); filtering happens before or during vector search depending on the index.
8. [REQ] Insert data in batches of 10,000-100,000 rows using `insert()` or bulk import; flush after batch inserts to persist segments to object storage before indexing.
9. [REQ] Call `create_index()` after inserting data and before loading; load the collection into query node memory with `load()` before searching — unloaded collections return errors.
10. [REQ] Use `consistency_level` (`Strong`, `Bounded`, `Eventually`, `Session`) per collection or per search; `Bounded` is the recommended default for balanced latency and freshness.
11. [REQ] Secure connections with TLS (`tls.mode=2`) and authenticate with username/password or RBAC (v2.1+); restrict `root` user access and create role-based users for applications.
12. [REQ] Monitor `search_latency`, `search_qps`, and segment count per collection; too many growing segments degrade search — trigger compaction via `compact()` periodically.
13. [REQ] Use Zilliz Cloud for managed Milvus when operational overhead is a concern; Zilliz provides auto-scaling, managed upgrades, and SLA-backed availability.
14. [PROHIBIT] Do not query a collection before `load()` completes; querying an unloaded collection raises an error and indicates a misconfigured application lifecycle.
15. [PROHIBIT] Do not change the vector `dim` or metric type after collection creation; these are immutable — create a new collection, migrate data, and drop the old one.
[COMPAT]
- v2.4+: Multi-vector hybrid search, Grouping search, Inverted index for scalar, iterator API
- v2.3+: DiskANN index, upsert support, bulk import, RBAC
- v2.1+: Partition key, dynamic schema, consistency levels
- Deployment: Docker Compose, Kubernetes (Milvus Operator), Zilliz Cloud (managed)
[REFS]
- https://milvus.io/docs
- https://milvus.io/docs/index
- https://milvus.io/docs/partition_key
- https://milvus.io/docs/scalar_index
- https://milvus.io/docs/deploy_s3
- https://zilliz.com/docs
