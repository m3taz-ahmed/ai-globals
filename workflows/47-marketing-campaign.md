[WORKFLOW] 47-marketing-campaign
[OBJ] Brief→channels→budget→launch→measure marketing campaign flow using `marketing-strategy` and paid/organic channel skills with ROAS and budget guardrails.
[TRIGGER] marketing campaign | حملة إعلانية | campaign | launch campaign | قنوات تسويق | growth
[RULES]
1. [REQ] Brief: capture objective, audience, KPI, and budget from the user before planning.
2. [REQ] Channels: select organic (social/content/SEO) + paid (Google/Meta/TikTok/LinkedIn) via relevant skills; free-first defaults.
3. [REQ] Budget: set caps and ROAS targets; hand off paid setup to `paid-ads` with cost gates.
4. [REQ] Launch: stage creative + tracking; require explicit approval before any live spend.
5. [REQ] Measure: pull `marketing-analytics` + `attribution_model` to report CAC/LTV/ROAS.
6. [REQ] Iter: pause underperforming ad sets per pre-agreed rules; log to `Memory.md`.
7. [REQ] Approval gate: no campaign launch or paid spend without explicit user approval.
[PROHIBIT]
1. No campaign launch or paid spend without explicit user approval.
2. No budget overrun beyond the approved cap.
3. No ToS violations on ad platforms.
4. Respect marketing-compliance: consent, unsubscribe, GDPR on captured leads.
