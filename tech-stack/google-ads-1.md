[TECH] google-ads-1
[OBJ] Google Ads API (Search/Display/YouTube) (2026). Closed-source platform. Use via official client libraries only. Free API; ad spend required.
[DATA]
- Version/License: Proprietary. Free API access via Google Ads API v17+. Requires Google Ads account + OAuth developer token (approved).
- Core Data Model: Customer → Campaign (type: SEARCH/DISPLAY/VIDEO/SHOPPING) → AdGroup → AdGroupAd (Ad creative) → AdGroupCriterion (keyword/audience) → BiddingStrategy → CampaignBudget. Conversion tracking via gclid.
- Free-tier/Limits: API free; default quota ~15,000 operations/day (standard), higher with token. Test account (no spend) for dev. Rate limits per token.
[API]
- Endpoint: `https://googleads.googleapis.com/v17/customers/{cid}/googleAds:search` (GAQL). Auth: OAuth2 + developer token. SDK: `google-ads` (Python/Node/Java/C# official).
- Key: `googleAds.search` (GAQL), `Mutate` for campaigns/ads. Offline conversion import via `uploadClickConversions`.
[CTX] Context7 ID: `websites/googleads_google-ads-api` (real)
[RTL]
- RTL note: Google Ads supports Arabic (RTL) ad text + keywords (target `ar` language + MENA geo). Ad previews render RTL. Use RSA (responsive search ads) with Arabic headlines. Landing page RTL for Arabic campaigns improves QS. Billing in local currency (SAR/AED/EGP).
[PROHIBIT] ⛔ No campaign launch without aiZee approval gate. ⛔ Respect policy (no restricted content). ⛔ Don't vendor SDK; use official client lib.
