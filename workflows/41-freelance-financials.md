[WORKFLOW] 41-freelance-financials
[OBJ] Income/expense/tax/cashflow planning for freelancers using `freelance-financials` skill and erpnext accounting patterns to manage volatile income, VAT, emergency fund, and retirement.
[TRIGGER] tax | ضريبة | cash flow | تدفق نقدي | savings | تخطيط مالي
[RULES]
1. [REQ] Intake: collect monthly income history, fixed/variable expenses, jurisdiction, and tax/VAT rate.
2. [REQ] Forecast: project cashflow across best/expected/worst cases using the user's volatile income pattern.
3. [REQ] Tax: estimate income tax/VAT owed per period; flag filing deadlines. Hand off to `freelance-financials` for the breakdown.
4. [REQ] Reserve: recommend an emergency fund and a retirement allocation as a percentage of net income.
5. [REQ] Record: persist the plan to the storage backend and summarize the position in `Memory.md`.
6. [REQ] Approval gate: no filing, no payment instruction, no outward financial communication without explicit user approval.
[PROHIBIT]
1. No tax filing, payment instruction, or financial submission without explicit user approval.
2. No giving of regulated financial/legal advice beyond estimations.
3. No ToS violations on financial platforms.
4. Respect marketing-compliance: never share financial data to third-party lists (GDPR).
