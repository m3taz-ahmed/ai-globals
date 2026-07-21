[FILE] Memory
[OBJ] Short-term context and cross-session continuity.
[RULES]
1. [REQ] Read at session start.
2. [REQ] Update at session end via `workflows/09-memory-sync.md`.
3. [REQ] Keep under 500 lines.
[UPDATED] 2026-07-21
[NOTES]
- Expanded *-lord skills to 11 domains (database, language, cloud-platforms, devops, frontend-frameworks, backend-frameworks, messaging-streaming, search-vector, ai-ml, linux-systems, security) and compressed them to Telegraphic Pseudo-Code.
- Fixed `runtime/tech_stack.py` version detection: matches hyphenated major-minor tech-stack filenames, parses `composer.json`/`package.json` constraints when lockfiles absent, and aliases common packages.
- Fixed `Dockerfile` `state/CHANGELOG.md` COPY bug; now creates `state/`/`brain/`/`graphify-out/` directories.
- Refreshed `graphify-out/` graph.
- Refactored `dashboard/server.py`: shared kernel/memory instances, configurable CORS origin, per-IP rate limiting, POST body validation.
- Refactored `runtime/mcp_client.py` to cache stdio processes per server/root and reuse initialized stdio connections.
- Updated `workflows/README.md` file count and added 11-14 audit workflows.
- Added `runtime/policies/examples/` (api-rate-limits, data-exfiltration, time-based-access) and recursive policy loading.
- Pinned `.github/workflows/ci.yml` action SHAs (actions/checkout, actions/setup-python) and documented SBOM/Cosign release step.
- Quality gates green: ruff, mypy, pytest, `python eval/harness.py`.
- Integrated 9 AI personas into `global-roles.md` (English) and created `global-roles-ar.md` (Arabic) for agent/IDE identity charters.
- Rewrote `README.md` and `README-AR.md` with clearer quickstart, persona showcase, updated architecture, and bilingual links.
- Implemented Auto Persona Selection: `runtime/persona.py` + integration in `runtime/kernel.py`, `runtime/workflow.py`, `cli.py`, and tests.
- Added `ai-os persona list/detect` and `ai-os agent spawn --persona auto`.
- Added persona skills `game-architect`, `google-play-warlord`, `mobile-game-producer` with Context7 IDs and `PERSONA_SKILLS` mapping.
- Fixed CI/CD: `graphify.yml` installs `graphifyy` and creates a PR; `ci.yml`/`validate.yml` use pinned SHAs + lighter `[dev]` install + `--no-cov`.
