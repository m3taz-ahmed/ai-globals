# Qdrant Vector Database Standards (RAG Integration)

> [!NOTE]
> **TRIGGER:** LOAD ON VECTOR SEARCH, RETRIEVAL-AUGMENTED GENERATION (RAG), OR SEMANTIC CACHING IMPLEMENTATIONS.
> **SCOPE:** OFFICIAL VECTOR DATABASE MANDATE.

## 1. ARCHITECTURE & HOSTING
- **Engine Selection:** Use **Qdrant** as the primary vector database engine due to its native Rust performance, payload filtering capabilities, and flexibility (self-hosted Docker or Cloud).
- **Data Sovereignty:** For internal enterprise data, prioritize local Docker deployment alongside the backend ecosystem.

## 2. COLLECTION DESIGN
- **Vector Dimensions:** Ensure collection dimensions perfectly match the embedding model output (e.g., 1536 for standard models, 768 for local models).
- **Distance Metric:** Use `Cosine` similarity as the standard metric for text embeddings unless specified otherwise.
- **Payload Indexing:** Always index payload fields used for metadata filtering (e.g., `tenant_id`, `document_type`) to ensure constant-time retrieval speeds.

## 3. RAG PIPELINE PROTOCOLS
- **Chunking Strategy:** Use semantic chunking or overlapping character chunking (e.g., 500 tokens with 50 token overlap) to preserve context continuity.
- **Hybrid Search:** Implement sparse-dense hybrid search combining keyword and dense vectors for optimal retrieval accuracy.
- **Tenant Isolation:** Enforce strict multi-tenancy by appending `tenant_id` filters to every retrieval request. Never mix tenant data collections without filter isolation.
