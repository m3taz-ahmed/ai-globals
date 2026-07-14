[FILE] global-workflow
[OBJ] Core exec loop/context.
[RULES]
1. [REQ] ColdStart: ALWAYS read `global-roles.md` & `global-workflow.md` first. ⛔ NO cache trust.
2. [CMD] L0: Load `rules/core-behavioral-compact.md`, `skills/`.
3. [CMD] L1: Load `.ai/active-context.md`, `rules/vocabulary.md`, `rules/anti-patterns.md`, `tech-stack/useful-repos.md`.
4. [CMD] L2: Lazy load `rules/*.md`, `workflows/*.md`.
5. [CMD] L3-VersionGate `[VER-01]`: ⛔ BEFORE loading ANY `tech-stack/` file, read `composer.lock` (PHP) or `package-lock.json` (JS) to detect exact major versions. Map detected versions to correct `tech-stack/<pkg>-<ver>.md`. ⛔ NEVER default to v3 for Filament or any other pkg. If lockfile missing, check `composer.json`/`package.json` constraints.
6. [REQ] Preflight: Check `skills/`, Anti-patterns(`[SEC-xx]`). ⛔ NO destructive bash w/o val.
7. [REQ] MCP-SYNC: ⛔ NEVER write implementation code for any framework/library without querying Context7 MCP (`get-library-docs`) first. Live Ground-Truths > LLM memory.
8. [REQ] Validate: If reqs <80% clear, PAUSE & ASK. ⛔ NO blind large-code gen. This rule is NOT about version detection. VER-01 handles that.
9. [REQ] Changelog: Update `CHANGELOG.md` `[Unreleased]` ONLY. NEVER edit past versions.
10. [REQ] State: Use `.task/` or `.gsap/` for complex tasks `[EXE-PERSIST-01]`. ⛔ NO chat memory trust. Ref `rules/EXAMPLES.md`.
11. [CMD] Handoff: Run `workflows/09-memory-sync.md` post-milestone.
12. [REQ] Knowledge Sync: If a novel bug is fixed or a workaround is found (e.g., framework-specific edge cases), ALWAYS document the solution as a new rule in the relevant `tech-stack/*.md` file to prevent recurrence.
13. [REQ] Context Sync: ALWAYS read `Memory.md` at the project root to understand short-term context/history. If missing or outdated, generate/update it in CAVEMAN format before closing the session to ensure cross-agent continuity.
14. [REQ] Git Constraint: NEVER interact with `git` (no commits, branching, merging, pushing, or pulling) unless the user EXPLICITLY requests it. When requested, perform ONLY the exact git operations asked, nothing more.
15. [CMD] Runtime Gate `[OS-EXE-01]`: Before ANY action, set `AGENT_OS_ROOT` if missing. Run `ai-os check <action> --args '{"tokens":N}'` or `Kernel.act` to validate policy + budget. If `deny`/`block`, STOP and report.
16. [CMD] Memory Sync `[OS-MEM-02]`: If `rules/`, `tech-stack/`, or `workflows/` changed, run `ai-os memory ingest` and `graphify update .`.
17. [CMD] MCP Sync `[OS-MCP-02]`: For IDE context, use `aios_mcp/config.json` or `python aios_mcp/aios_server.py`.
18. [CMD] Dashboard `[OS-DASH-01]`: For local dashboard, use `python dashboard/server.py 8080`. Use `AGENT_OS_DASHBOARD_TOKEN` for auth.
19. [CMD] Validation Gate `[OS-VAL-01]`: Before handoff, run `python eval/harness.py` and ensure `all_pass: true`. Fix all `ruff`/`mypy`/`pytest`/`validate-globals` failures first.
