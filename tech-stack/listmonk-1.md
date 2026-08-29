[TECH] listmonk-1
[OBJ] listmonk — self-hosted, Go-based newsletter + email automation engine (AGPL-3.0). Free-first alternative to hosted ESPs with full data sovereignty. Rules + data model for aiZee email-marketing skill.
[RULES]
1. [REQ] License: AGPL-3.0. Use as self-hosted service/plugin; do NOT vendor core code into aiZee (AGPL obligation). Deploy via Docker (`listmonk/listmonk:latest`) + Postgres.
2. [REQ] Data model (canonical): Lists → Subscribers (with arbitrary JSON attributes) → Campaigns (template + list + throttle) → Tx (transactional via `/api/tx`). Mirror exactly in email-marketing.
3. [REQ] API: REST (`/api/...`): `/lists`, `/subscribers` (GET/POST/PUT/DELETE + bulk import), `/campaigns`, `/templates`, `/tx`, `/media`. Auth: admin token or API token (scoped).
4. [REQ] Subscribers: attributes are free-form JSON (e.g. `{"locale":"ar","plan":"pro"}`). Use for segmentation + RTL routing. Double opt-in via `/subscribers/import` + confirmation template.
5. [REQ] Campaigns: choose lists, pick/template (HTML + plain-text), set `send_at` + rate limit (e.g. 100/s). Media stored in `/media`.
6. [REQ] i18n/ar: templates support `{{.Attributes.locale}}` and arbitrary attributes; render RTL by branching on `locale=ar` → `dir="rtl"`. listmonk UI is translatable; Arabic locale supported.
7. [REQ] Transactional: `/api/tx` sends single emails via a transactional template (welcome, receipt, OTP). Use for lifecycle triggers.
8. [REQ] Bounce/opt-out: built-in bounce processing + unsubscribe; honor `{{ UnsubscribeURL }}` in every template.
9. [REQ] Delivery: connect SMTP (Brevo/Postmark/Amazon SES) or send via built-in. Respect provider send limits; throttle campaigns.
10. [REQ] Webhooks/media: campaign analytics (views/clicks) via UI/API; export to `marketing-analytics` + GA4 (ga4-1).
11. [REQ] Free-first: $0 software cost (self-host). Only infra + SMTP sending cost. Preferred when Brevo free 300/day is insufficient or data must stay in-region (GDPR/MENA).
12. [PROHIBIT] ⛔ Vendor AGPL core into aiZee repo. ⛔ Send without opt-in + unsubscribe link. ⛔ Store API token in code/logs/commits. ⛔ LTR template to `locale=ar` subscribers.
13. [CMD] Context7: `knadh/listmonk`.
14. [REQ] Arabic/RTL note: branch templates on `Attributes.locale`; set `dir="rtl" lang="ar"`; Arabic font stack (Cairo/Tajawal).
