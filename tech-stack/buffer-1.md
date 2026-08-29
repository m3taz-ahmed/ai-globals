[TECH] buffer-1
[OBJ] Social media scheduling + analytics (2026). Closed-source SaaS. Use via API/SDK only. Free-first alternative in aiZee: Postiz (AGPL, recommended).
[DATA]
- Version/License: Proprietary SaaS. Free tier: 3 channels, 10 scheduled posts/channel (queue), no analytics on free (2024+). Paid from ~$6/channel/mo (Essentials) for analytics/calendar.
- Core Data Model: Profile (connected social account) â†’ Channel â†’ Post (text/media/schedule) â†’ Queue â†’ Tag â†’ Analytics (reach/clicks/engagement). Buffer Publish + Analyze + Engage.
- Free-tier/Limits: 3 social channels; 10 drafts/queued posts per channel; no Instagram Stories auto; no analytics/reporting; link shortening limited.
[API]
- Base: `https://api.bufferapp.com/1/`. Auth: OAuth2 access token.
- Key endpoints: `POST /user`, `GET /profiles`, `POST /profiles/{id}/updates` (schedule post), `GET /updates/pending`, `POST /updates/{id}/share`, `GET /profiles/{id}/analytics`.
- SDK: community `buffer-api-php`/`bufferapp` (Node). No official full SDK.
[CTX] Context7 ID: `websites/developers_buffer` 
[RTL]
- RTL note: Buffer composer is LTR; Arabic posts need manual RTL but publish correctly to X/IG/FB/LinkedIn (these render RTL natively). Character limits: X 280, IG caption 2,200, LinkedIn 3,000 â€” truncate Arabic gracefully. Emojis count as 2 chars on X. Schedule for MENA peak (20:00â€“23:00 GST).
[PROHIBIT] â›” No auto-posting without user approval gate (aiZee post_queue cost gate). â›” Do not vendor Buffer code. â›” Respect per-channel free caps.
