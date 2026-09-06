[TECH] MongoDB 8.3 (latest 8.3.7, Jul 2026)
[OBJ] MongoDB document database — rapid-release, major releases every 2 years, sequential minor upgrade requirement.
[RULES]
1. [REQ] Rapid-release model: minor releases ship frequently. Must upgrade minor releases sequentially (8.0 → 8.1 → 8.2 → 8.3) — never skip minor versions.
2. [REQ] MongoDB 8.2 EOL 31 Jul 2026 — upgrade to 8.3+ before EOL.
3. [REQ] Major releases every 2 years — plan migration windows accordingly.
4. [REQ] Use WiredTiger storage engine (default) — never use MMAPv1 (removed).
5. [REQ] Use replica sets for all production deployments — minimum 3 members for HA.
6. [REQ] Use `change streams` for CDC — watch collection/database/cluster level.
7. [REQ] Use aggregation pipeline for complex queries — `$match`, `$group`, `$lookup`, `$unwind`, `$facet`.
8. [REQ] Use indexes for all query fields — `createIndex()` with appropriate type (single, compound, text, geospatial).
9. [REQ] Use `mongosh` (not legacy `mongo` shell) for admin/queries.
10. [REQ] Use field-level encryption for PII — `ClientSideFieldLevelEncryption`.
11. [REQ] Use `db.collection.bulkWrite()` for batch operations — never loop individual inserts.
12. [REQ] Enable authentication + authorization (RBAC roles) in production — never run without auth.
13. [PROHIBIT] Never skip minor version upgrades — must upgrade sequentially.
14. [PROHIBIT] Never run 8.2 past EOL (31 Jul 2026) — upgrade to 8.3+.
15. [PROHIBIT] Never run production without replica set + authentication.
16. [PROHIBIT] Never use `eval()` or `$where` with user input — injection risk.
17. [PROHIBIT] Never use MMAPv1 — removed, use WiredTiger.
18. [CMD] `mongosh "mongodb://host:27017/db"` — connect.
19. [CMD] `mongod --replSet rs0` — start replica set member.
20. [CMD] `mongodump --uri="..." --out=/backup` — backup.
[COMPAT]
- MongoDB 8.3.7: latest (Jul 2026).
- 8.2 EOL: 31 Jul 2026.
- Sequential minor upgrade required (8.0 → 8.1 → 8.2 → 8.3).
- Major releases every 2 years.
- WiredTiger only (MMAPv1 removed).
- `mongosh` replaces legacy `mongo` shell.
[REFS]
- https://www.mongodb.com/docs/
- https://www.mongodb.com/docs/manual/release-notes/
- https://www.mongodb.com/docs/manual/reference/method/
