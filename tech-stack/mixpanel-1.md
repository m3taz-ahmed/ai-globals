[TECH] mixpanel-1
[OBJ] Product + marketing analytics (events/funnels/retention) (2026). Closed-source SaaS. Use via SDK/API. Free-first alternatives: PostHog/Umami (MIT). Free tier limited.
[DATA]
- Version/License: Proprietary SaaS. Free tier: 100K tracked events/month (MTU-based now), 1 project, 1 year data history, limited connectors. Paid from ~$20/mo (Growth, event/MTU based).
- Core Data Model: Project â†’ Event (name + props) â†’ User/Profile (distinct_id, super props) â†’ Board â†’ Funnel â†’ Retention â†’ Cohort â†’ Experiment (via integration). Lexicon for property governance.
- Free-tier/Limits: 100K events/mo free; no data pipelines/warehouse sync; limited group analytics; 1 year retention. Rate: 60 events/sec ingestion default.
[API]
- Endpoint: `https://mixpanel.com/api/2.0/`. Auth: Bearer `<PROJECT_TOKEN>` (query) or service account. SDK: `mixpanel` (JS/Node/Python/Android/iOS official).
- Key endpoints: `POST /track` (ingest via SDK), `GET /funnels`, `GET /retention`, `GET /insights`, `POST /query` (JQL/LEX). EU region available (GDPR).
[CTX] Context7 ID: `mixpanel/mixpanel-python` 
[RTL]
- RTL note: Mixpanel dashboards support RTL locale. Arabic event property values display fine. Build MENA funnels (Arabic step labels) for localized products. Set EU data residency for Arabic/EU users (GDPR). Reports export UTF-8.
[PROHIBIT] â›” No PII in event props without consent (GDPR). â›” Don't vendor SDK. â›” Respect 100K/mo free cap.
