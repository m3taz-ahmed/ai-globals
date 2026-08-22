[TECH] pgvector
[OBJ] PostgreSQL extension for vector similarity search providing vector type, IVFFlat and HNSW indexes, and seamless integration with SQL, transactions, and RLS.
[RULES]
1. [REQ] Install pgvector from source or package manager (`apt install postgresql-16-pgvector`); run `CREATE EXTENSION IF NOT EXISTS vector;` in each database that needs vector operations.
2. [REQ] Use `vector(N)` column type with explicit dimension; dimension is fixed per column and cannot be changed without `ALTER TABLE ... TYPE vector(M)` which rewrites the table.
3. [REQ] Choose index type by workload: IVFFlat for moderate datasets (<1M rows, lower build time, tunable `lists`), HNSW for larger datasets or lower latency (higher build time and memory, tunable `m` and `ef_construction`).
4. [REQ] For IVFFlat, set `lists = rows / 1000` as a starting heuristic; query with `probes` (default 1) — increase `probes` for higher recall at the cost of latency; set via `SET ivfflat.probes = 10`.
5. [REQ] For HNSW, set `m = 16` (connectivity, 16-64) and `ef_construction = 64` (build-time search width, 64-256); query with `hnsw.ef_search` (default 40) — increase for recall, decrease for speed.
6. [REQ] Build indexes after bulk data loading (`CREATE INDEX ... USING hnsw (col vector_cosine_ops)`); building on an empty table then inserting is slower and produces suboptimal graph structure.
7. [REQ] Use the correct operator class for your distance metric: `vector_cosine_ops` for cosine, `vector_l2_ops` for L2/Euclidean, `vector_ip_ops` for inner product; mismatched ops class ignores the index and does sequential scan.
8. [REQ] Use `<=>` (cosine), `<->` (L2), `<#>` (inner product) operators in `ORDER BY` clauses to trigger index usage; `ORDER BY col <=> query_vec LIMIT 10` is the canonical ANN query pattern.
9. [REQ] Combine vector search with standard SQL filters and joins in a single query: `WHERE category = 'x' ORDER BY embedding <=> query_vec LIMIT 10`; use pre-filtering for selective conditions to avoid ANN index bypass.
10. [REQ] Use Row Level Security (RLS) policies with vector columns to enforce tenant isolation: `CREATE POLICY tenant_isolation ON docs USING (tenant_id = current_setting('app.tenant_id')::uuid)`.
11. [REQ] Use pgvector 0.7.0+ for half-precision (`halfvec(N)`, 50% storage savings) and binary quantization (`bit(N)` with Hamming distance) for large-scale cost reduction.
12. [REQ] Use `pgvector` with `parallel` query execution for large tables; set `max_parallel_workers_per_gather` and ensure `enable_seqscan` is not disabled for fallback planning.
13. [REQ] Monitor index size, `pg_stat_user_indexes.idx_scan`, and `pg_statio_user_indexes.idx_blks_read`; HNSW indexes can be 2-5x the size of the vector data — plan memory accordingly.
14. [PROHIBIT] Do not use exact search (`ORDER BY ... LIMIT k` without an index) on tables with >100K rows in production; sequential scans on vector columns are O(n) and will time out under load.
15. [PROHIBIT] Do not mix distance metrics within the same index; a cosine index with L2 queries or vice versa bypasses the index and falls back to brute-force sequential scan.
[COMPAT]
- v0.7.0+: halfvec, binary quantization, SPQR index, iterative scans, parallel HNSW builds
- v0.6.0+: HNSW index, `vector_avg`, `vector_sum` aggregate functions
- v0.5.0+: IVFFlat index improvements, `halfvec` preview
- PostgreSQL 13+ required (14+ recommended for HNSW parallel builds)
[REFS]
- https://github.com/pgvector/pgvector
- https://github.com/pgvector/pgvector#installation
- https://github.com/pgvector/pgvector#indexing
- https://github.com/pgvector/pgvector#querying
- https://supabase.com/docs/guides/ai/vector-columns
- https://supabase.com/docs/guides/ai/vector-indexes
