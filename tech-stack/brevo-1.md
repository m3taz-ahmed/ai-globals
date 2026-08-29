[TECH] brevo-1
[OBJ] Brevo (formerly Sendinblue) — free-first Email Service Provider (ESP) for newsletters, transactional email, and marketing automation. Rules + API surface for aiZee email-marketing skill.
[RULES]
1. [REQ] Free tier: 300 emails/day, unlimited contacts, visual automation workflows, SMS (pay-as-you-go), CRM lite. No credit card to start. This is the aiZee default free-first ESP.
2. [REQ] Paid only as parity: higher daily limit, A/B testing, multivariate, remove logo. Recommend only when 300/day is exceeded.
3. [REQ] API surface: REST v3 (`https://api.brevo.com/v3`) + SMTP relay. Auth: `api-key` header (`X-API-Key`). Python SDK: `brevo-python` (`sib_api_v3_sdk`). Node: `@getbrevo/brevo`.
4. [REQ] Core resources: `/contacts` (create/update/list/attributes), `/contacts/lists`, `/emailCampaigns`, `/smtp/email` (transactional), `/automation` (workflows), `/transactionalSMS`.
5. [REQ] Double opt-in: create contact with `attributes` (locale, plan) + `listIds`; send confirmation email via `/smtp/email` or double opt-in template. Always store consent.
6. [REQ] Segmentation: use contact attributes (`locale`, `plan`, `engagement`) + list membership; build filtered lists server-side. For Arabic: attribute `locale=ar`, apply RTL template.
7. [REQ] Deliverability: configure SPF/DKIM/DMARC in Brevo domain settings; send plain-text + HTML; warm up new domains.
8. [REQ] GDPR/EU: Brevo is EU-hosted (GDPR). Honor right-to-erasure (`DELETE /contacts/{email}`), store consent timestamp, include mandatory unsubscribe footer (auto-added).
9. [REQ] Automation (drip): visual workflows trigger on contact add / list join / event; mirror `email-marketing` trigger→condition→action model. Throttle to free 300/day.
10. [REQ] Webhooks: inbound events (open/click/bounce/unsub) via `/webhooks`. Forward to `marketing-analytics` + GA4 (ga4-1) for attribution.
11. [REQ] RTL Arabic: send `dir="rtl" lang="ar"` HTML; Brevo editor supports RTL blocks. Subject ≤40 chars Arabic.
12. [PROHIBIT] ⛔ Send without opt-in + unsubscribe. ⛔ Exceed 300/day on free tier (queue/throttle). ⛔ Store API key in code/logs/commits. ⛔ Send LTR template to `locale=ar` contacts.
13. [CMD] Context7: `brevo/python-sdk` (fallback `sendinblue/bravo`).
14. [REQ] Free-first note: default over Mailchimp/SendGrid/Klaviyo when 300/day covers volume; self-host listmonk (listmonk-1) when sovereignty/scale needed.
