[TECH] lago-1
[OBJ] Open-source metering + billing engine (2026). AGPL-3.0 (getlago/lago, ~10k★). Self-host free. Use as external service/plugin — DO NOT vendor core code. aiZee billing/retainer option.
[DATA]
- Version/License: AGPL-3.0. Self-host free (Rails + Postgres + Clickhouse). Cloud paid. Powers usage-based billing/subscriptions.
- Core Data Model: Organization → Customer → Plan (charges: fixed/usage/graduated) → Subscription → Meter (event-based usage) → Event (ingest usage) → Invoice (PDF) → AddOn → Coupon. Webhooks for lifecycle.
- Free-tier/Limits: Self-host unlimited. Cloud free dev tier. Event ingestion via API/SDK. Invoice PDF generation built-in.
[API]
- Endpoint: `https://api.getlago.com/api/v1/`. Auth: Bearer `<API_KEY>`. SDK: `lago-ruby`, `lago-python`, `lago-js` (official).
- Key: `POST /events` (usage), `POST /subscriptions`, `POST /customers`, `POST /invoices`, `GET /analytics`. Webhooks for `invoice.created` etc.
[CTX] Context7 ID: `websites/getlago_lago` (real)
[RTL]
- RTL note: Lago invoices support localization; add Arabic invoice templates (RTL) + local currency (SAR/AED/EGP) for MENA clients. Self-host for data residency. Use for freelance retainer/usage billing in Arabic.
[PROHIBIT] ⛔ AGPL — never vendor/modify core for redistribution. ⛔ Use as service/plugin. ⛔ No invoice issue without approval gate.
