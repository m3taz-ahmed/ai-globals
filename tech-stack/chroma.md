[TECH] Chroma
[OBJ] Open-source embedded vector database designed for LLM applications with collections, metadata filtering, pluggable embedding functions, and client-server mode.
[RULES]
1. [REQ] Use Chroma in embedded mode (`PersistentClient`) for single-process applications and local development; use client-server mode (`HttpClient`) for multi-process or production deployments.
2. [REQ] Create collections with explicit `embedding_function` (e.g., `OpenAIEmbeddingFunction`, `SentenceTransformerEmbeddingFunction`, `CohereEmbeddingFunction`); default uses `all-MiniLM-L6-v2` from sentence-transformers.
3. [REQ] Pass `metadata` as a flat dict of strings, ints, floats, or booleans on each document; nested dicts and lists are not supported and will raise a ValueError.
4. [REQ] Use `where` filter with operators (`$eq`, `$ne`, `$gt`, `$gte`, `$lt`, `$lte`, `$in`, `$nin`) for metadata filtering at query time; combine with `where_document` for full-text document filtering.
5. [CMD] Use `collection.add(ids=[...], documents=[...], metadatas=[...], embeddings=[...])` for inserts; omit `embeddings` to let the configured embedding function compute them automatically.
6. [REQ] Use `collection.query(query_texts=[...], n_results=10, where={...})` for semantic search; `query_embeddings` for pre-computed vectors; results include `ids`, `documents`, `metadatas`, `distances`.
7. [REQ] Use `collection.update(ids=[...], documents=[...])` to modify existing documents; updating metadata requires passing the full metadata dict, not partial patches.
8. [REQ] Use Chroma Cloud for managed production deployments when you need scaling, backups, and monitoring without infrastructure management; local PersistentClient is not designed for concurrent multi-process access.
9. [REQ] Set `hnsw:space` to `cosine`, `l2`, or `ip` at collection creation via `CollectionMetadata`; the distance metric is immutable after creation — recreate the collection to change it.
10. [REQ] Configure `tenant` and `database` (v0.4.18+) for logical isolation in multi-tenant applications; each tenant-database pair is a separate namespace.
11. [REQ] Use `collection.count()` and `collection.peek(limit=10)` for health checks; `peek` returns a sample without full scans and is safe for monitoring.
12. [REQ] Persist the client path (`chromadb.PersistentClient(path="./chroma_db")`) to a stable directory; losing the path loses all data in embedded mode.
13. [PROHIBIT] Do not use `EphemeralClient` in production; it stores data in memory only and loses everything on process restart.
14. [PROHIBIT] Do not mix embedding functions across the same collection; changing the embedding function after documents are inserted produces inconsistent vector spaces and corrupt search results.
15. [PROHIBIT] Do not rely on Chroma embedded mode for concurrent write access from multiple processes; SQLite-based persistence does not handle concurrent writers — use HttpClient or Chroma Cloud instead.
[COMPAT]
- v0.5.0+: Tenant/database support, improved HNSW performance, async API
- v0.4.18+: Multi-tenancy, database isolation
- v0.4.0+: Client-server mode, OpenAI embedding function, where_document filter
- Deployment: Embedded (PersistentClient), Client-Server (HttpClient), Chroma Cloud (managed)
[REFS]
- https://docs.trychroma.com/
- https://docs.trychroma.com/usage-guide
- https://docs.trychroma.com/embeddings
- https://docs.trychroma.com/guides
- https://docs.trychroma.com/deployment/client-server-mode
- https://www.trychroma.com/chroma-cloud
