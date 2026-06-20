[FILE] global-workflow
[OBJ] Core execution loop and context loading blueprint.
[RULES]
1. [CMD] Layer 0: Load `rules/core-behavioral-compact.md`, `global-roles.md`, `skills/`.
2. [CMD] Layer 1: Load `./.ai/active-context.md`, `rules/vocabulary.md`, `rules/anti-patterns.md`, `tech-stack/useful-repos.md`.
3. [CMD] Layer 2/3: Lazy load `rules/*.md`, `tech-stack/` (via package.json), and `workflows/*.md`.
4. [REQ] Pre-flight: Check `skills/`. Check Anti-patterns (`[SEC-xx]`). ⛔ NO destructive bash without validation.
5. [REQ] Ask First: If reqs <80% clear, PAUSE and ask. ⛔ NO blind large-code generation.
6. [REQ] Persistent State: Use `.task/` or `.gsap/` hidden folders for complex tasks `[EXE-PERSIST-01]`. ⛔ DO NOT rely on chat memory. Reference `rules/EXAMPLES.md`.
7. [CMD] Handoff: Run `workflows/09-memory-sync.md` upon milestone completion.
