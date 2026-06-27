[FILE] global-workflow
[OBJ] Core exec loop/context.
[RULES]
1. [REQ] ColdStart: ALWAYS read `global-roles.md` & `global-workflow.md` first. ⛔ NO cache trust.
2. [CMD] L0: Load `rules/core-behavioral-compact.md`, `skills/`.
3. [CMD] L1: Load `.ai/active-context.md`, `rules/vocabulary.md`, `rules/anti-patterns.md`, `tech-stack/useful-repos.md`.
4. [CMD] L2/L3: Lazy load `rules/*.md`, `tech-stack/` (via pkg.json), `workflows/*.md`.
5. [REQ] Preflight: Check `skills/`, Anti-patterns(`[SEC-xx]`). ⛔ NO destructive bash w/o val.
6. [REQ] Validate: If reqs <80% clear, PAUSE & ASK. ⛔ NO blind large-code gen.
7. [REQ] Changelog: Update `CHANGELOG.md` `[Unreleased]` ONLY. NEVER edit past versions.
8. [REQ] State: Use `.task/` or `.gsap/` for complex tasks `[EXE-PERSIST-01]`. ⛔ NO chat memory trust. Ref `rules/EXAMPLES.md`.
9. [CMD] Handoff: Run `workflows/09-memory-sync.md` post-milestone.
10. [REQ] Knowledge Sync: If a novel bug is fixed or a workaround is found (e.g., framework-specific edge cases), ALWAYS document the solution as a new rule in the relevant `tech-stack/*.md` file to prevent recurrence.
11. [REQ] Context Sync: ALWAYS read `Memory.md` at the project root to understand short-term context/history. If missing or outdated, generate/update it in CAVEMAN format before closing the session to ensure cross-agent continuity.
