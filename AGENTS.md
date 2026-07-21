---
name: ai-global-os
description: Sovereign AI engineering control plane. Central source of truth for rules, workflows, tech-stack, memory, and multi-agent orchestration.
license: MIT
---

[FILE] AGENTS
[OBJ] Cross-tool canonical instruction for all AI coding agents.
[RULES]
1. [REQ] Cold Start: Read `global-roles.md` then `global-workflow.md` first. Never cache.
2. [REQ] Persona: Detect the user's persona with `ai-os persona detect "<user prompt>"` or `Kernel.detect_persona`; adopt the returned persona and read `skills/<skill>/SKILL.md` before acting.
3. [REQ] Load Context Layers: L0 `rules/core-behavioral-compact.md`, `skills/`; L1 `rules/vocabulary.md`, `rules/anti-patterns.md`, `tech-stack/useful-repos.md`; L2 `rules/*.md` + matched `tech-stack/<pkg>-<ver>.md`; L3 `workflows/*.md` per task.
4. [REQ] VersionGate `[VER-01]`: Before loading any `tech-stack/` file, read `composer.lock` or `package-lock.json` and load only the matching version file. Never default to v3 for Filament or v11 for Laravel.
5. [REQ] Use MCP: Query Context7 MCP for any external library/framework before implementing code. Never rely on memory.
6. [REQ] Graphify: If `graphify-out/graph.json` exists, use `query_graph`/`shortest_path`/`get_node` before raw grep/read. Run `graphify update .` after code edits.
7. [REQ] Memory: Read `state/MEMORY.md` at session start. Update it at end using `workflows/09-memory-sync.md`.
8. [REQ] Runtime: Route all tool calls through `runtime/` kernel when present. Obey `allow/ask/deny` policies.
9. [REQ] Cost: Check `runtime/budget` before every LLM call. Stop on hard cap.
10. [REQ] Quality: 0 linter warnings. SOLID/DRY/KISS. No `any` types. No inline imports. No raw SQL interpolation.
11. [REQ] Git: Conventional commits. Atomic. Never `git add .` or force push. Stage only files you modified.
12. [REQ] Root: Discover OS root from `AGENT_OS_ROOT` env or install dir. Never hardcode `D:/server/.ai`.
13. [REQ] Runtime Gate: Route all actions through `runtime/kernel.py` (Policy + Budget + Audit). Use `ai-os check <action> --args` or `Kernel.act` before execution.
14. [REQ] MCP: Use `aios_mcp/aios_server.py` as native MCP server. Prefer `query_rules`, `check_policy`, `search_memory`, `search_memory_vector`.
15. [REQ] Memory: Run `ai-os memory ingest` after any rule/tech-stack/workflow change.
16. [REQ] Quality: 0 linter warnings. Run `ruff check .`, `mypy`, `pytest -q`, `python eval/harness.py` before declaring done. No `eval` for policy.
17. [PROHIBIT] No unauthorized server actions. No destructive bash without validation. No `min/` folders. No generic UIs.
18. [REQ] Handoff: Run `workflows/09-memory-sync.md` after every milestone.
