# Tech-Stack: Meilisearch

> [!NOTE]
> **TRIGGER:** LOAD ON global search implementation, indexing records.
> **SCOPE:** Meilisearch (self-hosted), Laravel Scout integration.

## 1. Laravel Scout Integration
- Use the Laravel Scout Meilisearch driver.
- Define `toSearchableArray` in Eloquent models to strictly control the payload sent to Meilisearch.
- Utilize queueing for Scout index updates to prevent blocking HTTP requests.

## 2. Index Configuration
- Explicitly define `filterableAttributes`, `sortableAttributes`, and `searchableAttributes` upon index creation or via a migration script.
- Configure ranking rules (e.g., exactness, typo tolerance, proximity) tailored to the specific domain.
- Define synonyms and stop words to improve search relevancy.

## 3. Advanced Querying & Deployment
- Implement faceted search for complex filtering UIs on the frontend.
- Utilize multi-index search if querying across different models (e.g., Users and Documents) simultaneously.
- When self-hosting on EC2, manage API keys rigorously: use the Master Key only for configuration, and generate specific Search/Admin keys for application use.

## 4. Hard Constraints
- NEVER expose the Master Key to the frontend or commit it to version control.
- NEVER index sensitive data (e.g., passwords, private keys) in Meilisearch.
- ALWAYS batch index updates when importing large datasets to prevent overwhelming the Meilisearch instance.

---

## ✅ MEILISEARCH COMPLIANCE CHECK (Mandatory)
- [ ] **Security:** Are appropriate API keys (not the Master Key) used for application queries?
- [ ] **Configuration:** Are filterable and sortable attributes explicitly defined?
- [ ] **Performance:** Are Scout index updates queued asynchronously?
