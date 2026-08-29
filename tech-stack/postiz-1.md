[TECH] postiz-1
[OBJ] Self-hostable social media scheduling + analytics (Postiz app, gitroomhq) (2026). Free-first default in aiZee for social. AGPL-3.0 — use as external service/plugin, DO NOT vendor core code.
[DATA]
- Version/License: AGPL-3.0 (gitroomhq/postiz-app, ~32k★). Self-host free (Docker) or Postiz Cloud (free 1 channel, paid tiers). aiZee default social scheduler.
- Core Data Model: Channel (provider connection) → Provider (X/LinkedIn/IG/YT/TikTok/Threads/Mastodon via provider-interface) → Post (draft/schedule/approve) → Integration → Analytics. Temporal-based queue for reliability.
- Free-tier/Limits: Self-host = unlimited (your infra). Cloud free: 1 channel, limited posts/mo. Paid removes limits. Provider rate limits apply (e.g. X paid API).
[API]
- Self-hosted REST at `/api/`. Key concepts: provider-interface (each network = adapter implementing common `post()`/`refresh()`). Use Temporal workflows for schedule. No public REST docs stable — integrate via plugin wrapping provider-interface.
- SDK: None official; aiZee `social_tools.py` wraps provider-interface pattern.
[CTX] Context7 ID: `websites/gitroomhq_postiz-app` (real)
[RTL]
- RTL note: Postiz composer supports RTL; Arabic posts publish to X/IG/FB/LinkedIn with native RTL. Use `social_tools` provider ABC to unify char limits + RTL direction per platform. Schedule Arabic content for MENA evening peaks. Preview RTL in-app.
[PROHIBIT] ⛔ AGPL — never vendor/modify core for redistribution without license compliance. ⛔ No auto-publish without aiZee approval gate. ⛔ Respect X paid-API cost gate (post_queue).
