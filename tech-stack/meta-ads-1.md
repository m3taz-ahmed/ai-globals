[TECH] meta-ads-1
[OBJ] Meta (Facebook/Instagram) Ads marketing API (2026). Closed-source platform. Use via official SDK/API only. Free to create ads but requires ad spend + app review.
[DATA]
- Version/License: Proprietary platform. Free API access (Graph API) but ads require payment + Meta Business account + app in Development→Live with `ads_management` permission (review).
- Core Data Model: AdAccount → Campaign (objective) → AdSet (targeting/audience/budget/schedule) → Ad (creative) → AdCreative → Insight (metrics: impressions/clicks/spend/ROAS). Pixel + Conversions API for events.
- Free-tier/Limits: No free ad credits generally. API rate limit ~200 calls/user/60min (token-based). Sandbox/test accounts for dev without spend.
[API]
- Graph API: `https://graph.facebook.com/v19.0/`. Auth: OAuth access token (long-lived). SDK: `facebook_business` (Python/Node official).
- Key endpoints: `POST /act_{id}/campaigns`, `POST /act_{id}/adsets`, `POST /act_{id}/ads`, `GET /act_{id}/insights`, `POST /{pixel}/events` (CAPI).
[CTX] Context7 ID: `websites/facebook_facebook-python-business-sdk` (real)
[RTL]
- RTL note: Meta Ads Manager fully supports Arabic (RTL) ad copy + creative; set locale `ar_AR`. Audience targeting for MENA (SAR/AED/EGP) with city/interest layers. CAPI event names must match pixel. Landing pages should be RTL for Arabic campaigns; otherwise high bounce.
[PROHIBIT] ⛔ No ad launch without explicit aiZee approval gate. ⛔ Respect GDPR for EU audiences (consent). ⛔ Do not vendor Meta SDK beyond usage.
