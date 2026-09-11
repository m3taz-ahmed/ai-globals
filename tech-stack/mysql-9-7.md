[TECH] mysql-9-7
[OBJ] MySQL 9.7.0 LTS Advanced Schema Rules (Stable Apr 21 2026, latest 9.7.2 Jul 2026). Innovation track: MySQL 26.7 (calendar versioning YY.M.P, latest 26.7.1 Aug 2026).
[RULES]
1. [REQ] Vector: Native Vector types for AI semantic search. Vector indexes (cosine/L2). NOTE: Plain MySQL has NO vector distance functions — use MariaDB 11.7+ or MySQL HeatWave for `whereVectorSimilarTo()`.
2. [REQ] JS Stored Procedures: Use ONLY for complex JSON manipulation. Prefer native SQL. ⛔ NO filesystem/network access.
3. [REQ] Diagnostics: Performance schema for lock detection. Structured JSON error logging. Slow query (`long_query_time` 1s dev/2s prod).
4. [REQ] Calendar Versioning (26.7+): MySQL Innovation track uses `YY.M.P` format (e.g. 26.7.0). `MYSQL_PREVIOUS_LTS_VERSION` in `mysql_version.h` identifies the previous LTS (9.7.0). Use Innovation for latest features, LTS for production stability.
5. [REQ] Laravel AsVector Compatibility: Laravel 13.31+ `AsVector` cast does NOT work on plain MySQL (no native vector distance). Use MariaDB 11.7+ or PostgreSQL with pgvector for Laravel vector queries.
