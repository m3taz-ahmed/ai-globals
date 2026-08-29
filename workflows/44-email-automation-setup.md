[WORKFLOW] 44-email-automation-setup
[OBJ] Choose ESP→list→segment→drip→live setup for email marketing using the `email-marketing` skill (Brevo free-first, listmonk self-host) with compliant opt-in and unsubscribe.
[TRIGGER] email setup | نشرة بريدية | drip | campaign بريدي | newsletter | تسويق بريد
[RULES]
1. [REQ] ESP: recommend Brevo (free) or listmonk (self-host) per the `email-marketing` skill; note paid parity only.
2. [REQ] List: create/import a list with explicit opt-in only; reject purchased or scraped lists.
3. [REQ] Segment: build segments (locale, behavior, lifecycle) with RTL Arabic support.
4. [REQ] Drip: design the trigger→condition→action sequence via `drip_engine` patterns; include unsubscribe in every send.
5. [REQ] Live: dry-run, then request approval before going live. Hand off sends to `email_tools`.
6. [REQ] Compliance: run `marketing-compliance` check (opt-in/unsubscribe/GDPR) before any dispatch.
7. [REQ] Approval gate: no campaign send, no list write, without explicit user approval.
[PROHIBIT]
1. No email send, campaign, or list import/export without explicit user approval.
2. No purchased/scraped lists or non-opt-in sending.
3. No ToS violations on ESP platforms.
4. Respect marketing-compliance: mandatory opt-in, unsubscribe, GDPR on all broadcasts.
