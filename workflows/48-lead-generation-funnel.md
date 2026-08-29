[WORKFLOW] 48-lead-generation-funnel
[OBJ] Capture→score→nurture→handoff lead funnel using `lead-generation-crm` and `b2b-cold-outreach`, with `lead_scorer` qualification and CAN-SPAM-compliant outreach.
[TRIGGER] lead gen | اكتساب عملاء | lead funnel | عميل محتمل | prospecting | قمع مبيعات
[RULES]
1. [REQ] Capture: collect leads via forms/social/`community-builder` with explicit opt-in only.
2. [REQ] Score: run `lead_scorer` (fit/intent/behavior → 0-100) and route by tier.
3. [REQ] Nurture: build compliant drip via `drip_engine` + `email-marketing`; honor unsubscribe.
4. [REQ] Outreach: `b2b-cold-outreach` sequences must be CAN-SPAM/GDPR compliant; require approval per sequence.
5. [REQ] Handoff: sync qualified leads to CRM (`crm_manager`) and alert the user for personal close.
6. [REQ] Approval gate: no outbound message or CRM write without explicit user approval.
[PROHIBIT]
1. No outbound message, lead import, or CRM write without explicit user approval.
2. No purchased/scraped lists or non-opt-in cold email.
3. No ToS violations on outreach/CRM platforms.
4. Respect marketing-compliance: opt-in, unsubscribe, CAN-SPAM, GDPR mandatory.
