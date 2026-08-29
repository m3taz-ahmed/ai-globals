[TECH] flagsmith-1
[OBJ] Feature flags + remote config + segments (2026). BSD-3-Clause (flagsmith/flagsmith, ~6.5k★). SAFE licensing (BSD) — safe to reuse patterns. Self-host or Cloud.
[DATA]
- Version/License: BSD-3-Clause. Self-host free (Docker). Cloud free: 50k requests/mo, 3 environments, 10 flags, 1 project. BSD = use/reuse freely (keep notice).
- Core Data Model: Project → Environment (dev/staging/prod) → Feature (key + enabled + value) → Segment (rules: trait/identity match) → Identity (user, trait-based) → Trait. Rollout % + multivariate values.
- Free-tier/Limits: Cloud free = 50k requests/mo, 10 flags, 3 envs, 1 project. Self-host unlimited. SDK cached + polled locally.
[API]
- Endpoint: `https://api.flagsmith.com/api/v1/`. Auth: Bearer `<ENV_KEY>` (client) or admin token. SDK: `flagsmith`, `flagsmith-nodejs`, `flagsmith-flutter` (official multi-lang).
- Key: `GET /flags` (client), `POST /identities/{id}` (identity flags), `POST /features` (manage). Edge API available.
[CTX] Context7 ID: `websites/flagsmith_flagsmith` (real)
[RTL]
- RTL note: Flags support locale segments — use `trait: language == ar` to enable Arabic/RTL features (e.g. RTL UI, Arabic copy variants). Cohorts can target Arabic-speaking users. Safe BSD licensing to build aiZee `feature_flags.py` on this model.
[PROHIBIT] ⛔ BSD — keep copyright notice if reused. ⛔ Don't expose server admin key to client. ⛔ Guard paid limits on Cloud.
