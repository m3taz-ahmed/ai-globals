[TECH] plausible-1
[OBJ] Privacy-first web analytics (2026). AGPL-3.0 (plausible/analytics, ~29k★). Self-host free (recommended) or Plausible Cloud. Use as external service/plugin — DO NOT vendor core code.
[DATA]
- Version/License: AGPL-3.0. Self-host Docker = free unlimited. Cloud from ~$9/mo (10K pageviews). aiZee analytics option (privacy-first).
- Core Data Model: Site (domain) → Pageview → Event (custom goal) → Session (cookieless, IP hashed) → Source/Referrer/UTM → Funnel (goal sequences) → Country/Device/Browser. No per-user profiles (GDPR by design).
- Free-tier/Limits: Self-host unlimited. Cloud free trial only. Data collected via lightweight 1KB script (`/js/script.js` or `.outbound-links.js`). No API free tier (Cloud API paid).
[API]
- Self-hosted: data via script post to `/api/event`. Stats API (Cloud) `https://plausible.io/api/v1/stats/...` (Bearer token). No official SDK; embed script.
- Concepts: goals = events; funnels = goal → goal. Shared/team dashboards.
[CTX] Context7 ID: `websites/plausible_analytics` (real)
[RTL]
- RTL note: Plausible dashboard supports RTL (Arabic UI). Perfect for Arabic sites — cookieless, no consent banner needed (GDPR/MENA friendly). Track Arabic goal names; UTM for Arabic campaigns. Self-host keeps data in-region (data residency for Gulf).
[PROHIBIT] ⛔ AGPL — never vendor/modify core for redistribution. ⛔ No PII collection (not designed for it). ⛔ Use as service only.
