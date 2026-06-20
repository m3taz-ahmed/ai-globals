[TECH] mysql-9-7
[OBJ] MySQL 9.7.0 Advanced Schema Rules (Speculative/Preview).
[RULES]
1. [REQ] Vector: Native Vector types for AI semantic search. Vector indexes (cosine/L2).
2. [REQ] JS Stored Procedures: Use ONLY for complex JSON manipulation. Prefer native SQL. ⛔ NO filesystem/network access.
3. [REQ] Diagnostics: Performance schema for lock detection. Structured JSON error logging. Slow query (`long_query_time` 1s dev/2s prod).
