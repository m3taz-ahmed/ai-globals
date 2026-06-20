[TECH] mysql-8-4
[OBJ] MySQL 8.4 Architecture & Optimization.
[RULES]
1. [REQ] Schema: Precise datatypes. Foreign Keys with `ON DELETE`. Invisible columns for metadata.
2. [REQ] Indexes: Primary Key required. Composite indexes for multi-column filters. Functional indexes for expressions.
3. [PROHIBIT] Queries: Avoid `SELECT *`.
4. [REQ] Advanced: Use CTEs, Window Functions, and `EXPLAIN ANALYZE`.
