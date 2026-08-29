[WORKFLOW] 39-pricing-strategy
[OBJ] Compute recommended rate→present→negotiate flow for freelance pricing using `pricing-strategy` skill and `runtime/pricing_calculator.py` to derive value-based, hourly, project, retainer, or package rates.
[TRIGGER] pricing | تسعير | rate | retainer | حزمة | value-based
[RULES]
1. [REQ] Inputs: collect income target, fixed expenses, tax/VAT, platform fees, and utilization from the user before computing.
2. [REQ] Compute: call `pricing_calculator.py` to produce a recommended rate across models (hourly/project/retainer/package/value-based).
3. [REQ] Present: hand off to `pricing-strategy` to generate a bilingual rate card and a price-increase message template.
4. [REQ] Negotiate: provide 2-3 defensible pricing options and a BATNA. Never reveal the absolute floor without user consent.
5. [REQ] Record: log the chosen model and rate in `Memory.md` for reuse in proposals and invoices.
6. [REQ] Approval gate: no rate sent to a client, no price-change message, without explicit user approval.
[PROHIBIT]
1. No pricing quote, rate card, or price-change message to a client without explicit user approval.
2. No disclosure of absolute floor rate without explicit user consent.
3. No ToS violations on platforms regarding fee disclosure.
4. Respect marketing-compliance for any outbound pricing promotion (opt-in/unsubscribe/GDPR).
