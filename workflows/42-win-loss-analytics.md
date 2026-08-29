[WORKFLOW] 42-win-loss-analytics
[OBJ] Track bids→win rate→A/B proposals flow that turns freelance pipeline data into actionable conversion insights using `pipeline_analytics` patterns.
[TRIGGER] win loss | تحليل فوز | win rate | bid analytics | مراجعة عروض | pipeline review
[RULES]
1. [REQ] Capture: log every bid/proposal (platform, niche, rate, outcome) to `pipeline_analytics`.
2. [REQ] Measure: compute win rate, average rate by outcome, and drop-off points per platform/niche.
3. [REQ] A/B: run proposal variant experiments (cover letter, pricing options, CTA) and attribute wins to the winning variant.
4. [REQ] Insight: surface 2-3 concrete adjustments (profile, pricing, positioning) weekly.
5. [REQ] Record: write the win/loss summary to `Memory.md` for reuse in `pricing-strategy` and proposals.
6. [REQ] Approval gate: no outward client communication or profile change from insights without explicit user approval.
[PROHIBIT]
1. No client message, bid, or profile update driven by analytics without explicit user approval.
2. No fabrication of win/loss data.
3. No ToS violations on analytics or platform scraping.
4. Respect marketing-compliance: aggregated data only; no personal client data shared (GDPR).
