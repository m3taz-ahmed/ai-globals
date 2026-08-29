[TECH] posthog-1
[OBJ] Open-source product analytics + replay + feature flags + experiments (2026). MIT (PostHog/posthog, ~39k★). SAFE TO COPY PATTERNS (MIT). Free-first default in aiZee. Self-host or Cloud.
[DATA]
- Version/License: MIT. Self-host free (Docker/k8s, needs Redis+ClickHouse+Postgres). Cloud free: 1M events/mo, 15K session replays, 1M flag requests. MIT = safe pattern reuse.
- Core Data Model: Project → Event (with `$props`) → Person (distinct_id, merge) → Action (defined event) → Funnel → Retention → Cohort → FeatureFlag → Experiment (A/B, Bayesian). Session replay + heatmaps built-in.
- Free-tier/Limits: Cloud free = 1M events/mo, 15K replays, 1M flag reqs. Self-host unlimited (your infra). Ingestion via SDK or `/capture` endpoint.
[API]
- Endpoint: `https://app.posthog.com/api/`. Auth: Bearer `<PROJECT_TOKEN>`. SDK: `posthog-js`, `posthog-python`, `posthog-node` (official multi-lang). `POST /capture`, `POST /batch`, `GET /api/projects/@current/insights`.
- MCP: PostHog ships MCP server (integrates `analytics_tools`/`cro_tools`).
[CTX] Context7 ID: `websites/PostHog_posthog` (real)
[RTL]
- RTL note: PostHog dashboards support RTL/Arabic locale. Replay + heatmaps work on RTL pages. Cohorts can target Arabic users; run A/B on Arabic copy/CTA. **Free-first default** for aiZee analytics/CRO. Self-host for MENA data residency.
[PROHIBIT] ⛔ MIT — keep attribution if reused. ⛔ No PII in event props without consent. ⛔ Respect 1M/mo free cap on Cloud.
