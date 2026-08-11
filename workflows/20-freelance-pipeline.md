[WORKFLOW] 20-freelance-pipeline
[OBJ] End-to-end freelance job-to-contract pipeline: profile, search, score, proposal, approval, submit, follow-up — with MCP automation and explicit human gates.
[TRIGGER] freelance
[RULES]
1. [REQ] Intake: confirm primary platform(s), niche/specialty, minimum rate, weekly availability, preferred contract type, and scam/risk tolerance.
2. [REQ] Profile gate: run a quick profile audit using `freelance-platforms` rules. Do not start search until critical profile gaps are fixed.
3. [REQ] Search: use MCP (Upwork/Freelancer/Fiverr-research) or manual filters. Build a markdown shortlist with columns: platform, title, budget, client signal, score, link, next action.
4. [REQ] Score: rate every opportunity 0-100 across niche fit, client quality, budget realism, competition, and description clarity. Drop anything below the user's threshold and explain why.
5. [REQ] Draft: write a tailored proposal/bid with a platform-specific cover letter, 2-3 pricing options, and a clear CTA. Save to a temporary note and wait for approval.
6. [REQ] Approval gate: get an explicit `yes` before any bid, message, profile update, or contract action. If the user declines, revise or move to the next job.
7. [REQ] Submit: call the relevant MCP tool to place the bid/proposal. Record the proposal ID, platform, client, bid amount, and deadline.
8. [REQ] Follow-up: track client messages, interviews, and contract awards. Update `Memory.md` after each meaningful interaction.
9. [REQ] Win/loss review: weekly, summarize submitted bids, interviews, and conversions. Suggest profile/proposal/pricing adjustments.
[PROHIBIT]
1. No bid, message, contract, or profile update without explicit user approval.
2. No Fiverr bidding or messaging automation (ToS violation).
3. No work outside platform payment protection until a signed/escrowed contract is confirmed.
