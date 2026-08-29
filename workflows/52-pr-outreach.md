[WORKFLOW] 52-pr-outreach
[OBJ] Query match→pitch→follow-up PR outreach flow using `pr-pitch` skill to match journalist queries (HARO-style) and draft compliant pitches.
[TRIGGER] pr outreach | press release | HARO | علاقات صحفية | PR | pitch journalist
[RULES]
1. [REQ] Query match: scan journalist/PR queries and match to the user's expertise and assets.
2. [REQ] Pitch: draft a concise, non-promotional pitch via `pr-pitch`; include credentials and a clear angle.
3. [REQ] Approve: present the pitch for explicit user approval before any send.
4. [REQ] Follow-up: schedule one polite follow-up; never spam reporters.
5. [REQ] Record: log placements/responses in `Memory.md` for `marketing-analytics`.
6. [REQ] Approval gate: no pitch send or follow-up without explicit user approval.
[PROHIBIT]
1. No pitch send or follow-up without explicit user approval.
2. No spam, false claims, or undisclosed compensation to journalists.
3. No ToS violations on PR platforms.
4. Respect marketing-compliance: GDPR on journalist contacts; opt-in where required.
