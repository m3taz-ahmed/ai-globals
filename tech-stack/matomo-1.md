[TECH] matomo-1
[OBJ] Open-source web + marketing analytics (2026). GPL-3.0 (matomo-org/matomo, ~22k★). Self-host free (core). Use as external service — DO NOT vendor core code (GPL). Official RTL/Arabic support.
[DATA]
- Version/License: GPL-3.0. Self-host free (core analytics). Cloud from ~€21/mo. Premium plugins paid. Strong privacy/GDPR + official RTL.
- Core Data Model: Site (idsite) → Visit (action=pageview/event/download/goal) → Goal (conversion) → Segment → Funnel → Campaign (mtm_ UTM attribution) → Referrer/Keyword → Custom Dimension → Report (API).
- Free-tier/Limits: Self-host core unlimited (your server). On-prem needs DB. Heatmaps/sessions (premium). HTTP API rate modest.
[API]
- Endpoint: `https://your.matomo/api/?module=API&method=...&format=json&token_auth=...`. Auth: token_auth. Methods: `VisitsSummary.get`, `Goals.get`, `Events.getCategory`, `Funnels.get`, `Live.getLastVisitsDetails`.
- SDK: `matomo-php-tracker`, JS tracker (`matomo.js`). Official tracking + Reporting API.
[CTX] Context7 ID: `websites/matomo-org_matomo` (real)
[RTL]
- RTL note: Matomo has **official Arabic translation + RTL admin UI** — ideal for MENA. Campaign attribution via `mtm_` params + referrer. Goal funnels for Arabic conversion paths. Self-host keeps data in-region (Gulf data residency). Track Arabic page titles/events seamlessly.
[PROHIBIT] ⛔ GPL — don't vendor/redistribute modified core without license. ⛔ Respect visitor privacy (opt-out available). ⛔ Use as service/plugin.
