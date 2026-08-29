[TECH] growthbook-1
[OBJ] Open-source A/B testing + feature flags (2026). MIT (growthbook/growthbook, ~9k★). SAFE TO COPY PATTERNS (MIT). Self-host or Cloud. aiZee experiment_tracker/feature_flags basis.
[DATA]
- Version/License: MIT. Self-host free (Node + Postgres/Redis). Cloud free: 3 users, unlimited experiments, 1 SDK. MIT = safe to reuse stats engine.
- Core Data Model: Project → Feature (flag + rules + conditions) → Experiment (hypothesis, variation, goal metric) → Metric (custom/funnel/ratio) → Attribution/Exposure → Result (CUPED/Bayesian/SRM). SDK streams config.
- Free-tier/Limits: Self-host unlimited. Cloud free: 1 environment, 3 seats. Stats engine (`packages/stats`) is MIT — reuse in `experiment_tracker.py`.
[API]
- Endpoint: `https://api.growthbook.io/api/`. Auth: Bearer `<KEY>`. SDK: `growthbook` (JS/Node/Python/Go/Ruby/Android/iOS official). Streaming/`getFeatures` + `track` experiment exposure.
- Key: `POST /api/v1/experiments`, `POST /api/v1/features`, `POST /api/v1/track` (exposure). `packages/stats` for Bayesian/CUPED math.
[CTX] Context7 ID: `websites/growthbook_growthbook` (real)
[RTL]
- RTL note: Experiments can target Arabic locale (`attribute language=ar`) to run RTL UI variants. MIT stats engine safe to copy into aiZee `experiment_tracker` (CUPED/SRM/Bayesian). Goal metrics for Arabic conversion funnels.
[PROHIBIT] ⛔ MIT — keep attribution if reused. ⛔ No experiment without approval gate. ⛔ Guard Cloud free seat limits.
