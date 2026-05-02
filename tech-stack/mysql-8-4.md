# MySQL 8.4 Architecture & Optimization

## 1. SCHEMA DESIGN
- **Datatypes:** Use precise types (`INT` vs `BIGINT`, `VARCHAR` limits). Always use `TIMESTAMP` or `DATETIME` correctly.
- **JSON Columns:** Use JSON fields only for dynamic, unstructured data (like settings). Do not use JSON to bypass proper relational normalization.
- **Foreign Keys:** ALWAYS define foreign keys with appropriate `ON DELETE` cascades or restrictions for data integrity.
- **Invisible Columns:** Use invisible columns for metadata (like `deleted_at`) that shouldn't clutter `SELECT *` (though `SELECT *` is discouraged).

## 2. INDEXING STRATEGY
- Every table must have a Primary Key.
- Add Indexes on any column used frequently in `WHERE`, `JOIN`, `ORDER BY`, or `GROUP BY` clauses.
- Use Composite Indexes for queries that filter by multiple columns simultaneously.
- **Functional Indexes:** Use functional indexes for queries that filter based on expressions (e.g., `INDEX ((LOWER(email)))`).

## 3. QUERY OPTIMIZATION
- Avoid `SELECT *`. Only fetch the required columns.
- Utilize MySQL 8.x features: Common Table Expressions (CTEs) for recursive queries, and Window Functions (`ROW_NUMBER()`, `RANK()`) for complex analytical reporting.
- **EXPLAIN ANALYZE:** Use `EXPLAIN ANALYZE` to identify bottlenecks in complex queries.