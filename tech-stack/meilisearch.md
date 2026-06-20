[TECH] meilisearch
[OBJ] Meilisearch Integration (Laravel Scout).
[RULES]
1. [REQ] Integration: Use Scout Meilisearch driver. Strictly control payload via `toSearchableArray`. Queue index updates.
2. [REQ] Config: Define `filterableAttributes`, `sortableAttributes`, synonyms, rankings.
3. [PROHIBIT] Security: NEVER expose Master Key. NEVER index PII/secrets.
4. [REQ] Performance: Batch large dataset imports.
