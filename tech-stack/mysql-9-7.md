# MySQL 9.7.0 Advanced Schema Rules
> [!SPECULATIVE] This version is not yet in general production use. Rules are based on preview/RC documentation. Verify against official release notes before applying.

## 1. VECTOR SEARCH & AI INTEGRATION
- **Native Vectors:** Utilize native Vector data types and functions for AI-driven semantic search instead of relying on external databases (Pinecone, Weaviate).
- **Vector Indexes:** Create vector indexes with appropriate distance metrics (cosine, L2, inner product) based on the embedding model used.
- **Hybrid Queries:** Combine vector similarity search with traditional WHERE clauses for filtered semantic search.

## 2. JAVASCRIPT STORED PROCEDURES
- **Use Case:** Leverage JavaScript-based stored procedures only for complex JSON manipulations where standard SQL falls short.
- **Security:** JS stored procedures run in a sandboxed environment. Never expose filesystem or network access through them.
- **Performance:** Prefer native SQL for simple operations. JS procedures add overhead and should be reserved for truly complex transformations.

## 3. OBSERVABILITY & DIAGNOSTICS
- **Performance Schema:** Use the enhanced performance schema for preemptive lock detection and query bottleneck identification.
- **Error Logging:** Configure structured JSON error logging for integration with centralized log aggregation (ELK, Loki).
- **Slow Query Analysis:** Set `long_query_time` to 1s in development, 2s in production. Review slow query logs weekly.