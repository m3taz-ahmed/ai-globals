[TECH] formbricks-1
[OBJ] Open-source surveys + experience management / CRO (2026). AGPL-3.0 (formbricks/formbricks, ~13k★). Self-host free. Use as external service/plugin — DO NOT vendor core code.
[DATA]
- Version/License: AGPL-3.0. Self-host free (Next.js + Postgres). Cloud from ~$49/mo. aiZee cro_survey option.
- Core Data Model: Survey (type: link/app/popover/website) → Question (NPS/rating/MC/text) → Response → Action (webhook/integration) → Product (context) → Trigger (on event). Logic jumps + variables.
- Free-tier/Limits: Self-host unlimited surveys/responses. Cloud free tier limited (e.g. 1k responses/mo). API + MCP app available (integrates with aiZee cro_tools).
[API]
- Endpoint: `https://your.formbricks/api/`. Auth: Bearer `<API_KEY>`. Methods: `POST /api/v1/management/surveys`, `GET /api/v1/management/responses`, `POST /api/v1/client/responses` (submit). MCP server shipped.
- SDK: JS embed `<script>` survey trigger.
[CTX] Context7 ID: `websites/formbricks_formbricks` (real)
[RTL]
- RTL note: Formbricks supports RTL surveys (Arabic UI) — ideal for MENA CRO. Use popover/website surveys on Arabic RTL landing pages (set `dir="rtl"`). Capture NPS in Arabic. Self-host for data residency.
[PROHIBIT] ⛔ AGPL — never vendor/modify core for redistribution. ⛔ No survey injected without user consent/approval. ⛔ Use as service/plugin.
