[WORKFLOW] 45-social-content-calendar
[OBJ] Draft→approve→schedule→publish→measure social content flow across X/IG/YT/TikTok/LinkedIn using the `social-media-marketing` skill and Postiz scheduling patterns.
[TRIGGER] social calendar | جدولة منشورات | content calendar | تواصل اجتماعي | وسائل التواصل | schedule post
[RULES]
1. [REQ] Draft: create bilingual (AR/EN) posts per channel specs via `social-media-marketing`; respect character limits and RTL.
2. [REQ] Approve: present the weekly calendar for explicit user approval before any scheduling.
3. [REQ] Schedule: queue posts via `post_queue` with per-platform cost/limit gates (e.g., X cost gate).
4. [REQ] Publish: dispatch only approved items through `social_tools`; never auto-publish unapproved.
5. [REQ] Measure: pull `social_analytics` and feed results to `marketing-analytics`.
6. [REQ] Compliance: honor platform ToS and Arabic RTL rendering.
7. [REQ] Approval gate: no schedule, no publish, without explicit user approval.
[PROHIBIT]
1. No post schedule or publish without explicit user approval.
2. No auto-publishing of unapproved content.
3. No ToS violations on any social platform.
4. Respect marketing-compliance: no spam, opt-out honoring, GDPR on collected handles.
