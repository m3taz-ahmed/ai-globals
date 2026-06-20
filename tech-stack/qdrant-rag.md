[TECH] qdrant-rag
[OBJ] Qdrant Vector Database Standards (RAG).
[RULES]
1. [REQ] Engine: Qdrant (Rust, payload filtering).
2. [REQ] Collection: Dimensions MUST match embedding model (1536/768). Metric: `Cosine`. Index payload fields used for filtering (`tenant_id`).
3. [REQ] RAG: Semantic chunking (500 tokens / 50 overlap). Hybrid Search (sparse + dense).
4. [PROHIBIT] Isolation: NEVER mix tenant data without strict `tenant_id` filter appended to retrieval requests.
