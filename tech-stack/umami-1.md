[TECH] umami-1
[OBJ] Simple privacy-friendly web analytics (2026). MIT (umami-software/umami, ~38k★). SAFE TO COPY PATTERNS (MIT). Self-host free. aiZee analytics option.
[DATA]
- Version/License: MIT. Self-host free (Next.js + DB: PostgreSQL/MySQL). Cloud paid optional. MIT = safe to reuse event schema/patterns.
- Core Data Model: Website (domain) → Event (type=pageview/custom, with `data` props + session_id + referrer + country) → Session (grouped events, 1hr idle) → Metric (aggregate) → Goal (event-based). No cookies; anonymized IP.
- Free-tier/Limits: Self-host unlimited. Cloud free tier (~10K events/mo). Lightweight script. Data stored in your DB (full ownership).
[API]
- Endpoint: `https://your.umami/api/`. Auth: Bearer/API share token. Methods: `POST /api/send` (track), `GET /api/websites/{id}/stats`, `GET /api/websites/{id}/events`, `GET /api/websites/{id}/metrics`.
- SDK: JS script `umami.js`; official `umami` npm for tracking. Schema is MIT — reuse for `funnel_tracker.py`/`event_store`.
[CTX] Context7 ID: `websites/umami-software_umami` (real)
[RTL]
- RTL note: Umami dashboard supports RTL (Arabic locale). MIT event schema is safe to copy for aiZee `funnel_tracker`/analytics. Track Arabic page titles/goals; self-host for Gulf data residency. No cookie banner needed (privacy-first).
[PROHIBIT] ⛔ MIT = free to reuse, but keep attribution. ⛔ No PII in event `data` without consent. ⛔ Use self-host for ownership.
