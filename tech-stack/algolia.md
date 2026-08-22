[TECH] Algolia
[OBJ] Hosted search-as-a-service platform with instant search, faceting, personalization, A/B testing, Recommend API, and Algolia AI (NeuralSearch, Dynamic Re-Ranking, Query Suggestions).
[RULES]
1. [REQ] Design index schema with searchable attributes ordered by priority; the first attribute in `searchableAttributes` has the highest weight in relevance scoring — put the most important field first.
2. [REQ] Use `attributesForFaceting` with `filterOnly()` prefix for filter-only facets (no display) to reduce index size; use `searchable()` for facets that need both filtering and display counts.
3. [REQ] Batch operations with `saveObjects` in chunks of 1,000-5,000 records; use `waitTask` after batch operations to confirm indexing completion before dependent queries in test environments.
4. [REQ] Use `customRanking` with numeric or boolean attributes (e.g., `desc(popularity)`, `desc(rating)`) to break ties in text relevance; custom ranking is applied after textual relevance as a tiebreaker.
5. [REQ] Use the `filters` parameter with facet-based boolean expressions (`category:Book AND price<50`); use `facetFilters` for OR/AND combinations with arrays; escape quotes in string facet values.
6. [REQ] Enable personalization with `enablePersonalization: true` in search params and configure personalization strategy via the Dashboard or API with weighted events and facets.
7. [REQ] Use A/B testing via the Analytics API to compare ranking strategies; set `variant` assignments and track conversion events; minimum sample size and duration are required for statistical significance.
8. [REQ] Use the Recommend API (`/recommend` endpoint) with `recommendOptions` for related items, frequently-bought-together, and trending items; requires event tracking to be enabled and populated.
9. [REQ] Enable Algolia AI NeuralSearch for hybrid keyword + neural vector search; use `mode: 'hybrid'` or `mode: 'neural'` in search params; requires embedding model configuration and indexed vector data.
10. [REQ] Use Dynamic Re-Ranking to automatically optimize result order based on user engagement signals; enable per index in the Dashboard and allow 2-4 weeks for model training before evaluating impact.
11. [REQ] Use Query Suggestions API to generate autocomplete suggestions from search analytics; configure `minHits` and `minLetters` thresholds to filter noisy suggestions; deploy as a separate suggestions index.
12. [REQ] Secure API keys with scoped permissions; use Secured API Keys (generated from search-only keys) for frontend with `restrictIndices`, `restrictSources`, and `validUntil` constraints; rotate keys periodically.
13. [REQ] Use `replica` indices for alternative sorting strategies (e.g., `price_asc`, `rating_desc`); replicas share data with the primary index but maintain their own ranking configuration — update primary and replicas sync automatically.
14. [PROHIBIT] Do not use the Admin API key in client-side code; generate scoped Secured API Keys with minimal permissions (search-only, restricted indices, time-limited) for browser applications.
15. [PROHIBIT] Do not exceed 10 KB per record or 1,000 attributes per record; oversized records are rejected on indexing and degrade search performance — store large content externally and reference by URL.
[COMPAT]
- v3 API (2024+): NeuralSearch (hybrid mode), Dynamic Re-Ranking v2, Recommend API v2
- v2 API: Personalization, A/B testing, Query Suggestions, Rules, Synonyms
- REST API + client SDKs: JavaScript, Python, PHP, Ruby, Java, Go, Swift, Kotlin, C#
- Regions: US (us-east-1), EU (eu-west-1), DE (eu-central-1), AU (ap-southeast-2)
[REFS]
- https://www.algolia.com/doc/
- https://www.algolia.com/doc/guides/search/hits/ranking/
- https://www.algolia.com/doc/guides/managing-results/refine-results/faceting/
- https://www.algolia.com/doc/guides/personalization/
- https://www.algolia.com/doc/rest-api/recommend/
- https://www.algolia.com/doc/guides/ai/neural-search/
