[TECH] twenty-crm-1
[OBJ] Open-source CRM (metadata-driven) (2026). AGPL-3.0 (twentyhq/twenty, ~56k★). Self-host free. Use as external service/plugin — DO NOT vendor core code. Free-first default in aiZee for CRM.
[DATA]
- Version/License: AGPL-3.0. Self-host free (Node + Postgres + Redis). Cloud from ~$10/user/mo. aiZee lead-generation-crm default. Metadata-driven custom objects.
- Core Data Model: Workspace → Object (Company/Person/Opportunity/Note/Task/Activity — all metadata-defined) → Field (custom, typed) → Record → Pipeline (stage) → View (filter/sort) → Relation (associate). API auto-generated from metadata.
- Free-tier/Limits: Self-host unlimited users/records. Cloud free: limited seats. GraphQL + REST APIs, rate-limited. Realtime via WebSocket.
[API]
- Endpoint: `https://your.twenty/api/rest/` + `graphql`. Auth: Bearer `<API_KEY>` (or session). SDK: `@twentyhq/client` (TS), REST/GraphQL. Auto CRUD per object: `POST /rest/companies`, `POST /rest/people`, `POST /rest/opportunities`.
- Key: `POST /rest/{object}`, `GET /rest/{object}/search`, `POST /graphql` (metadata queries). Webhooks for record events.
[CTX] Context7 ID: `websites/twentyhq_twenty` (real)
[RTL]
- RTL note: Twenty UI supports RTL (Arabic locale). Custom fields accept Arabic values; pipeline stages in Arabic. Metadata-driven model ideal for Arabic-speaking CRUD (`crm_manager.py`). Self-host for MENA data residency. **Free-first CRM default**.
[PROHIBIT] ⛔ AGPL — never vendor/modify core for redistribution. ⛔ Use as service/plugin only. ⛔ No record create/sync without approval gate.
