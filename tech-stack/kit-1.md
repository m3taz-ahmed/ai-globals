[TECH] kit-1
[OBJ] Email marketing for creators (formerly ConvertKit) (2026). Closed-source SaaS. Use via API/SDK only. Free-first alternative in aiZee: Brevo / listmonk.
[DATA]
- Version/License: Proprietary SaaS. Free tier: unlimited subscribers but only ~10,000/month sends cap with Kit branding + broadcasts only (no visual automation on free, sequences limited). Paid from ~$15/mo for automation/sequences.
- Core Data Model: Subscriber (with tags + custom fields + sequences) â†’ Form (landing/page) â†’ Broadcast (one-time) / Sequence (autoresponder) â†’ Tag/Segment â†’ Rule (triggerâ†’action). Commerce (sell products) optional.
- Free-tier/Limits: Free for <~1,000 subs includes landing pages + forms + broadcasts. No visual automation builder on free (sequences of limited steps). Paid unlocks funnels/automations/reporting.
[API]
- Base: `https://api.kit.com/v4/`. Auth: Bearer `<PAT>` (personal access token) or OAuth.
- Key endpoints: `GET/POST /subscribers`, `POST /subscribers/{id}/tags`, `POST /broadcasts`, `POST /sequences/{id}/subscriptions`, `GET /forms`, `GET /tags`.
- SDK: community `kit-python` / `convertkit` wrappers; official REST only.
[CTX] Context7 ID: `websites/developers_kit` 
[RTL]
- RTL note: Kit forms/landing pages default LTR; use custom CSS `direction:rtl` for Arabic. Email broadcasts are HTML â€” wrap Arabic in `<div dir="rtl" lang="ar">`. Sequence delay logic works for any locale; localize timing for MENA (avoid Fri Jumu'ah send). Subject UTF-8.
[PROHIBIT] â›” No purchased lists; double opt-in recommended (Kit Enforce double opt-in). â›” Do not vendor Kit code. â›” Free tier shows Kit branding â€” remove via paid.
