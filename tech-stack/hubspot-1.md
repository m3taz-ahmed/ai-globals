[TECH] hubspot-1
[OBJ] CRM + marketing + sales automation (2026). Closed-source SaaS. Use via official API/SDK only. Free-tier CRM available; marketing paid.
[DATA]
- Version/License: Proprietary SaaS. Free CRM: contacts/deals/tasks (unlimited users, 1M contacts cap, limited to free tools). Marketing Hub paid from ~$20/mo (starter) for automation/email.
- Core Data Model: Contact (properties) â†’ Company â†’ Deal (pipeline/stage/amount) â†’ Engagement (email/meeting/call) â†’ List (segment) â†’ Workflow (automation) â†’ Form â†’ Ticket. Associations (associate objects).
- Free-tier/Limits: Free CRM: 1M contacts, basic forms, no automation workflows (paid). API: 100K calls/day (free tier) + per-endpoint rate (e.g. 40 req/10s contacts).
[API]
- Endpoint: `https://api.hubapi.com/`. Auth: OAuth2 / private app token (Bearer). SDK: `@hubspot/api-client` (Node), `hubspot-api-client` (Python official).
- Key: `POST /crm/v3/objects/contacts`, `POST /crm/v3/objects/deals`, `POST /crm/v3/objects/companies`, `POST /marketing/v3/emails`, `GET /crm/v3/objects/{type}/search`.
[CTX] Context7 ID: `hubspot/hubspot-api-nodejs` 
[RTL]
- RTL note: HubSpot supports Arabic (RTL) in email/Landing pages + forms; set locale `ar`. CRM properties accept Arabic values. Use for Arabic-speaking pipeline stages. GDPR + consent fields available for MENA/EU.
[PROHIBIT] â›” No automation/email send without approval gate + consent. â›” Don't vendor SDK. â›” Respect free API rate (100K/day).
