[WORKFLOW] 49-marketing-analytics
[OBJ] Collect→attribute→dashboard→decide marketing analytics flow using the `marketing-analytics` skill and GA4/Matomo/Plausible patterns for CAC/LTV/attribution.
[TRIGGER] ga4 | analytics | attribution | CAC | LTV | تحليل تسويق | mixpanel
[RULES]
1. [REQ] Collect: pull metrics from GA4/Matomo/Plausible/Mixpanel via `analytics_tools`; respect EU endpoints for GDPR.
2. [REQ] Attribute: run `attribution_model` (last/first/linear/position) and `funnel_tracker` drop-off.
3. [REQ] Dashboard: build a bilingual (AR/EN) dashboard (CAC, LTV, ROAS, conversion) via `analytics_dashboard`.
4. [REQ] Decide: surface 2-3 data-backed actions and route to the owning workflow (campaign/CRO/email).
5. [REQ] Record: persist insights to `Memory.md` for cross-workflow reuse.
6. [REQ] Approval gate: no outward data share or automated budget action without explicit user approval.
[PROHIBIT]
1. No data export/share or automated budget change without explicit user approval.
2. No PII storage without consent.
3. No ToS violations on analytics platforms.
4. Respect marketing-compliance: GDPR on visitor/lead data; opt-in for any retargeting.
