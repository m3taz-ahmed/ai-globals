[TECH] sendgrid-1
[OBJ] Transactional + marketing email via Twilio SendGrid (2026). Closed-source SaaS. Use via API/SDK only â€” do NOT vendor. Free-first alternative in aiZee: Brevo / listmonk.
[DATA]
- Version/License: Proprietary SaaS (Twilio). Free tier: 100 emails/day forever (trial); no free marketing/automation. Paid from $19.95/mo (2025 pricing) for 50K/mo + automation.
- Core Data Model: Sender/Verified Identity â†’ Contact (recipient, custom fields) â†’ List/Segment â†’ Single Send (campaign) / Automation (journey) â†’ Event (delivered/open/click/bounce/spam). Templates (dynamic, Handlebars).
- Free-tier/Limits: 100 emails/day free (trial, no CC). No marketing campaigns on free. Web API v3 rate limit ~2,000 req/10s shared. Suppression groups required for unsubscribe compliance.
[API]
- Base: `https://api.sendgrid.com/v3/`. Auth: Bearer `<API_KEY>`.
- Key endpoints: `POST /mail/send` (transactional), `POST /marketing/contacts`, `PUT /marketing/lists`, `POST /marketing/singlesends`, `GET /marketing/stats`, `POST /events/webhook` (inbound events).
- SDK: `sendgrid-python`, `sendgrid-nodejs`. Official. Event webhook for open/click/bounce.
[CTX] Context7 ID: `sendgrid/sendgrid-nodejs` 
[RTL]
- RTL note: SendGrid dynamic templates use Handlebars; wrap Arabic body in `<div dir="rtl" lang="ar">`. Bare sender authentication (DKIM/SPF) mandatory or mail lands in spam. RTL subject lines need UTF-8 encoding (`=?UTF-8?B?...?=`). Preview RTL in Gmail/Apple Mail.
[PROHIBIT] â›” No sending without verified sender + unsubscribe header (SendGrid auto-adds). â›” Do not vendor Twilio code. â›” Respect 100/day free cap; exceed â†’ paid only.
