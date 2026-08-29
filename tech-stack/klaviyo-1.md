[TECH] klaviyo-1
[OBJ] E-commerce email/SMS marketing + automation (2026). Closed-source SaaS, strong Shopify/Store integration. Use via API/SDK only. Free-first alternative in aiZee: Brevo / listmonk.
[DATA]
- Version/License: Proprietary SaaS. Free tier: 250 contacts + 500 email sends/month + 150 SMS/month (MVP plan). Paid from ~$20/mo scaling with profiles.
- Core Data Model: Profile (person, custom properties + predictive analytics) â†’ List/Segment (dynamic) â†’ Campaign (email/SMS) â†’ Flow (visual automation, triggerâ†’filterâ†’action) â†’ Event (tracked from store) â†’ Metric (open/click/order/revenue).
- Free-tier/Limits: 250 active profiles; 500 emails/mo; 150 SMS/mo; limited flows (1 active flow on MVP). Predictive analytics (CLV) paid only.
[API]
- Base: `https://a.klaviyo.com/api/`. Auth: Bearer `<PRIVATE_API_KEY>` (v2024-10-15+ versioned).
- Key endpoints: `POST /profiles`, `POST /profiles/{id}/lists`, `POST /campaigns`, `POST /flows`, `POST /events`, `GET /metrics/{id}/timeline`.
- SDK: `klaviyo-api-node`, `klaviyo-api-python`. Official.
[CTX] Context7 ID: `websites/developers_klaviyo_en` 
[RTL]
- RTL note: Klaviyo template editor supports RTL blocks for Arabic; set `dir="rtl"` on container. SMS to MENA (SAR/AED/EGP) supported via regional carriers â€” mind Unicode (UCS-2) billing per message segment. Revenue attribution works for Arabic-store SKUs.
[PROHIBIT] â›” No SMS without explicit opt-in (TCPA/GDPR). â›” Do not vendor Klaviyo code. â›” Free MVP = 1 flow only; exceed â†’ paid.
