[FILE] global-workflow
[OBJ] Core execution loop and context loading blueprint.
[RULES]
1. [REQ] Cold Start: ALWAYS read `global-roles.md` and `global-workflow.md` explicitly at the start of EVERY new session or task. ⛔ DO NOT rely on cached context for core rules.
2. [CMD] Layer 0: Load `rules/core-behavioral-compact.md`, `skills/`.
3. [CMD] Layer 1: Load `./.ai/active-context.md`, `rules/vocabulary.md`, `rules/anti-patterns.md`, `tech-stack/useful-repos.md`.
4. [CMD] Layer 2/3: Lazy load `rules/*.md`, `tech-stack/` (via package.json), and `workflows/*.md`.
5. [REQ] Pre-flight: Check `skills/`. Check Anti-patterns (`[SEC-xx]`). ⛔ NO destructive bash without validation.
6. [REQ] Ask First: If reqs <80% clear, PAUSE and ask. ⛔ NO blind large-code generation.
7. [REQ] Persistent State: Use `.task/` or `.gsap/` hidden folders for complex tasks `[EXE-PERSIST-01]`. ⛔ DO NOT rely on chat memory. Reference `rules/EXAMPLES.md`.
8. [CMD] Handoff: Run `workflows/09-memory-sync.md` upon milestone completion.
