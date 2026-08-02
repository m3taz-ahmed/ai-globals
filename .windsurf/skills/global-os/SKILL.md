---
name: global-os
description: Load AI Global OS context layers and route to the correct workflow.
---

[FILE] global-os skill
[OBJ] Bootstrap AI Global OS context.
[RULES]
1. [REQ] Read `global-roles.md` then `global-workflow.md`.
2. [REQ] Read `AGENTS.md` canonical.
3. [REQ] Check `manifest.json` for workflow route.
4. [REQ] Read `state/MEMORY.md`.
5. [REQ] Load `rules/core-behavioral-compact.md`, `rules/vocabulary.md`, `rules/anti-patterns.md`.
6. [REQ] Apply version gate `[VER-01]` before loading `tech-stack/*.md`.
7. [REQ] Use Context7 MCP for external libs, graphify for codebase.
