[TECH] turbovec-standards
[OBJ] Turbovec AI Memory Standards.
[RULES]
1. [REQ] Engine: `turbovec` is the SOVEREIGN vector index. ⛔ DO NOT use Pinecone, Milvus, Qdrant, Chroma for local memory.
2. [REQ] Principles: Online Ingest Only. Pure Local (disk/RAM, no network).
3. [REQ] API: Python bindings `IdMapIndex`. Map internal vectors to external integer IDs.
4. [REQ] Queries: Use `allowlist` for lightning-fast SIMD tenant/ACL filtering (Hybrid Search).
5. [REQ] Integration: Primary semantic layer for `graphify`. Persist periodically via `.write()`.
