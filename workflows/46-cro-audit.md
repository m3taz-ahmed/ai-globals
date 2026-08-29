[WORKFLOW] 46-cro-audit
[OBJ] Funnel→replay→hypothesis→experiment conversion-rate-optimization audit using the `cro-optimization` skill and PostHog/GrowthBook patterns, with statistical significance gating.
[TRIGGER] cro | معدل تحويل | landing page | تجربة أ ب | a/b test | conversion audit
[RULES]
1. [REQ] Funnel: map the funnel (visit→signup→lead→client) and compute drop-off via `funnel_tracker`.
2. [REQ] Replay: pull session replays/heatmaps (`cro_replay`/`cro_heatmap`) to locate friction.
3. [REQ] Hypothesis: form a ranked hypothesis list (copy, layout, CTA) using `copy-frameworks`.
4. [REQ] Experiment: run A/B via `experiment_tracker` (CUPED/SRM/Bayesian); wait for significance before declaring a winner.
5. [REQ] Apply: propose the winning variant to `social-media-marketing`/landing pages; require approval to ship.
6. [REQ] Compliance: no personally identifiable replay storage without consent (GDPR).
7. [REQ] Approval gate: no experiment launch or live change without explicit user approval.
[PROHIBIT]
1. No experiment launch or live page change without explicit user approval.
2. No early-stop on non-significant results (SRM/CUPED gating).
3. No ToS violations on analytics platforms.
4. Respect marketing-compliance: consent for replay/heatmap; GDPR on visitor data.
