[WORKFLOW] 50-marketing-automation
[OBJ] Trigger→enrich→route→notify marketing automation flow using `marketing-automation` skill and n8n/automatisch patterns to build compliant lifecycle journeys.
[TRIGGER] automation | journey | أتمتة تسويق | marketing automation | zapier | رحلة آلية
[RULES]
1. [REQ] Trigger: define the event trigger (signup, cart, lead tier) and guard with consent state.
2. [REQ] Enrich: augment the record via `crm_manager`/`lead_scorer`; reject data from non-opt-in sources.
3. [REQ] Route: build the trigger→condition→action graph (n8n/automatisch style) and map to `drip_engine`.
4. [REQ] Notify: alert humans on high-value branches; hand off sends to `email_tools`/`social_tools`.
5. [REQ] Test: dry-run the journey before live; require approval to activate.
6. [REQ] Compliance: run `marketing-compliance` (opt-in/unsubscribe/GDPR) on every branch.
7. [REQ] Approval gate: no journey activation or outbound action without explicit user approval.
[PROHIBIT]
1. No journey activation or outbound action without explicit user approval.
2. No automation on non-opt-in contacts.
3. No ToS violations on automation platforms.
4. Respect marketing-compliance: mandatory opt-in, unsubscribe, GDPR on all flows.
