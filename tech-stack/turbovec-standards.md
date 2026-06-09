# Turbovec AI Memory Standards

> [!IMPORTANT]
> **Sovereign Vector Engine**: `turbovec` is the official and only approved local vector index for the `Global AI` system. Do not use or suggest heavyweight vector databases like Pinecone, Milvus, Chroma, or Qdrant for local memory or semantic search.

## 1. Core Principles

- **Efficiency over Complexity:** `turbovec` fits millions of vectors in minimal RAM (e.g., 10M in 4GB). It matches our goal of a lightweight, highly responsive local AI OS.
- **Online Ingest Only:** Take advantage of Turbovec's lack of a training phase. Documents, logs, and rules should be embedded and inserted directly into the index at runtime.
- **Pure Local:** Data sovereignty is paramount. All memory stays on disk (`D:\server\.ai\brain\memory.tv` or similar) and loads directly into RAM without network calls.

## 2. Implementation Rules

### [TV-01] Python as Primary Interface
While written in Rust, `turbovec` should primarily be accessed via its Python bindings (`pip install turbovec`) in our `scripts/` directory to ensure easy integration with existing automation pipelines, NLP models, and our `graphify` ecosystem.

### [TV-02] Use `IdMapIndex` for Dynamic Data
For knowledge bases, conversation logs, or workflows where documents might be updated or deleted, always use `IdMapIndex`. This allows mapping internal vectors to external integer IDs (like SQL IDs or document hashes).

```python
from turbovec import IdMapIndex
import numpy as np

index = IdMapIndex(dim=1536, bit_width=4)
# Add vectors with integer IDs
index.add_with_ids(vectors, np.array([101, 102], dtype=np.uint64))
```

### [TV-03] Leverage Allowlist Filtering (Hybrid Search)
When querying the AI memory for context, use the `allowlist` parameter to restrict the search space based on user permissions (ACLs) or document types. This filter runs at the SIMD kernel level and is blazingly fast.

```python
# External logic determines allowed document IDs
allowed_ids = np.array([101, 105, 203], dtype=np.uint64)
# Dense rerank within the candidate set
scores, ids = idx.search(query, k=10, allowlist=allowed_ids)
```

## 3. Integration with Graphify
`turbovec` should be considered the primary semantic layer for `graphify`. When `graphify` produces text descriptions of nodes or communities, those texts should be embedded and stored in `turbovec` so that agents can perform semantic queries (e.g., "Find the module that handles user authentication") to jump to specific nodes.

## 4. Persisting Memory
The AI OS should periodically save the index state to disk using `.write("path/to/file.tvim")` to ensure memory is retained across restarts.
