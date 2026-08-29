[TECH] chatwoot-1
[OBJ] Open-source omnichannel customer support/community (2026). MIT (chatwoot/chatwoot, ~36k★). SAFE TO COPY PATTERNS (MIT). Self-host free. aiZee community-builder/whatsapp-sms option.
[DATA]
- Version/License: MIT. Self-host free (Rails + DB). Cloud from ~$19/agent/mo. MIT = safe to reuse channel-adapter patterns.
- Core Data Model: Account → Inbox (channel: Website/WhatsApp/FB/IG/Telegram/Email) → Conversation → Message → Contact → Agent (assignee) → Label → Campaign (mass outreach, opt-in). Canned responses + automation rules.
- Free-tier/Limits: Self-host unlimited agents/inboxes. Cloud free: 1 agent, 1 inbox. API rate modest. WhatsApp via Cloud API (Meta) needs business number.
[API]
- Endpoint: `https://your.chatwoot/api/v1/`. Auth: `api_access_token` header. SDK: official `chatwoot` ruby/node; REST mostly.
- Key: `POST /accounts/{id}/contacts`, `POST /accounts/{id}/conversations`, `POST /inboxes`, `POST /campaigns/{id}/messages`. Webhooks for events.
[CTX] Context7 ID: `websites/chatwoot_chatwoot` (real)
[RTL]
- RTL note: Chatwoot has **full RTL (Arabic) UI support** — ideal for MENA community/WhatsApp. Channel adapters reusable (MIT) for aiZee `community-builder`/`whatsapp-sms`. Arabic auto-replies + Canned responses in Arabic. Opt-in mass campaigns required.
[PROHIBIT] ⛔ MIT — keep attribution if reused. ⛔ No unsolicited WhatsApp broadcast (opt-in required). ⛔ Use self-host for ownership/scale.
