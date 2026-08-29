[WORKFLOW] 36-client-onboarding
[OBJ] Structured client intake→contract→invoice→kickoff flow for new freelance engagements: collect client details, trigger contract-studio, trigger invoice-manager for the first deposit, and hand off to a delivery plan.
[TRIGGER] onboarding | استقبال عميل | kickoff | intake form | عقد جديد | client setup
[RULES]
1. [REQ] Intake: send an RTL/English-aware intake form (client name, company, scope, budget, timeline, timezone, communication channel). Do not proceed without these basics.
2. [REQ] Profile check: confirm the engagement matches the user's niche, minimum rate, and availability before drafting anything.
3. [REQ] Contract: hand off to `contract-studio` to generate the NDA/SOW/MSA. Wait for the user's explicit approval before any signing action.
4. [REQ] Invoice: hand off to `invoice-manager` to emit the first deposit/quote. Do not send without approval.
5. [REQ] Kickoff: produce a delivery plan (milestones, deliverables, review cadence) and a client portal link. Save the plan to a note for the user.
6. [REQ] Memory: record client, contract ID, deposit status, and kickoff date in `Memory.md`.
7. [REQ] Approval gate: every contract, invoice, or message to the client requires an explicit `yes` from the user.
[PROHIBIT]
1. No contract, invoice, message, or profile update without explicit user approval.
2. No ToS violations on any freelance or client platform.
3. No sending of client communications (email/DM/portal) without explicit user approval.
4. Respect marketing-compliance for any follow-up: opt-in, unsubscribe, and GDPR where applicable.
