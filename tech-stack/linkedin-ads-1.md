[TECH] linkedin-ads-1
[OBJ] LinkedIn Marketing/Ads API (2026). Closed-source platform. Use via official API only. Free API (limited); ad spend required + partner/developer approval (gated).
[DATA]
- Version/License: Proprietary. LinkedIn Marketing API access requires approved developer app + `r_ads`/`rw_ads` permissions (approval gated, often partner program). Free to call; ads need spend.
- Core Data Model: Account â†’ CampaignManager (account) â†’ Campaign (objective) â†’ CampaignGroup â†’ Creative (single-image/video/document) â†’ Audience (Matched/Budget). Insights via reporting API.
- Free-tier/Limits: API free but throttled (~100 calls/min). Access approval required (LinkedIn reviews app). No self-serve free credits.
[API]
- Endpoint: `https://api.linkedin.com/rest/`. Auth: OAuth2 (member token) + x-restli-protocol-version. SDK: `linkedin-api` (unofficial) / REST only (official minimal).
- Key endpoints: `POST /adAccounts/{id}/campaigns`, `POST /adAccounts/{id}/creatives`, `GET /adAnalytics` ( reporting via `adAnalytics` query).
[CTX] Context7 ID: `websites/learn_microsoft_en-us_linkedin_marketing` 
[RTL]
- RTL note: LinkedIn supports Arabic (RTL) ad copy + landing for MENA B2B audiences. B2B targeting by job title/company/industry strong for Gulf. Creative text RTL-aware; CTA button direction. Audience in Arabic-speaking markets growing.
[PROHIBIT] â›” No ad launch without aiZee approval gate. â›” Access gated â€” don't assume token works. â›” Don't vendor code; REST only.
