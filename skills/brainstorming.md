---
name: brainstorming
description: Brainstorming and ideation skill.
---
[SKILL] brainstorming
[OBJ] Explore intent, requirements, and design before implementation.
[RULES]
1. [PROHIBIT] Hard Gate: NO coding, scaffolding, or implementation skills until design is presented and user approved.
2. [REQ] Process:
   - Explore: Read files/docs to understand state.
   - Clarify: Ask ONE question at a time. Understand constraints.
   - Propose: Give 2-3 technical options with trade-offs + recommendation.
   - Present: Write design spec. Get user approval.
   - Review: Fix inline TODOs/TBDs.
   - Next Step: Route to `writing-plans`. Do NOT start implementation.
3. [REQ] Clarifying questions that matter: ask about the decision-changing unknowns (constraints, scale, non-negotiables, existing pieces) — not everything. One at a time, each question admits an easy answer; batch trivial details into assumptions you state.
4. [REQ] Options must differ structurally: 2-3 options that take genuinely different trade-offs (speed-vs-flexibility, build-vs-buy, simple-vs-scalable) — three skins of the same approach is fake choice. Each gets pros/cons/fit in one line each.
5. [REQ] Recommendation required: never present options and shrug — pick one, say why in one sentence, note the case where another wins. Users approve decisions, not menus.
6. [REQ] Scope honesty: name what's explicitly OUT of scope in the proposal; surface the second-order cost (maintenance, migration, lock-in) not just the build cost.
7. [REQ] Assumption ledger: every unstated assumption the proposal rests on gets listed — wrong assumptions caught at design are free; caught at implementation are expensive.
8. [REQ] Design spec is terse: goal, chosen approach + why, key decisions, file/component boundaries, acceptance criteria — a spec that takes longer to read than to implement is overhead, not rigor.
9. [PROHIBIT] Implementation-detail rabbit holes before the shape is agreed; asking questions already answered by the codebase/docs; presenting a single option as a "choice"; or silently expanding scope between proposal and plan.
