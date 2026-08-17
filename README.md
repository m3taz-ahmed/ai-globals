<div align="center">
  <img src="logo.png" width="160" alt="aiZee Logo">
  <h1>aiZee</h1>
  <p><strong>The policy layer for AI coding.</strong></p>

  <p>
    <img src="https://img.shields.io/badge/Version-5.0.0-6C63FF?style=for-the-badge&logo=buffer&logoColor=white&labelColor=1a1a2e" alt="Version 5.0.0">
    <img src="https://img.shields.io/badge/Tests-2343%20passed-00C896?style=for-the-badge&logo=pytest&logoColor=white&labelColor=1a1a2e" alt="Tests: 2343 passed">
    <img src="https://img.shields.io/badge/Coverage-91%25-10B981?style=for-the-badge&logo=codecov&logoColor=white&labelColor=1a1a2e" alt="Coverage 91%">
    <img src="https://img.shields.io/badge/License-MIT-3B82F6?style=for-the-badge&logo=opensourceinitiative&logoColor=white&labelColor=1a1a2e" alt="License: MIT">
  </p>
  <p>
    <img src="https://img.shields.io/badge/Personas-19-EC4899?style=for-the-badge&logo=buffer&logoColor=white&labelColor=1a1a2e" alt="19 Personas">
    <img src="https://img.shields.io/badge/Skills-66-10B981?style=for-the-badge&logo=checkmarx&logoColor=white&labelColor=1a1a2e" alt="66 Skills">
    <img src="https://img.shields.io/badge/Workflows-36-0EA5E9?style=for-the-badge&logo=checkmarx&logoColor=white&labelColor=1a1a2e" alt="36 Workflows">
    <img src="https://img.shields.io/badge/Features-63%20total-F59E0B?style=for-the-badge&logo=sparkles&logoColor=white&labelColor=1a1a2e" alt="63 total features">
  </p>
</div>

---

[Read this in Arabic](README-AR.md) · [Changelog](CHANGELOG.md) · [Installer Guide](#installation)

---

## What is aiZee?

A **zero-compromise, version-controlled operating system** that sits between you and every AI coding assistant — Cursor, Claude, Copilot, Windsurf, Cline, Aider, Devin — enforcing engineering standards, security policies, and architectural discipline on every line of generated code.

**The problem it solves:** AI assistants hallucinate APIs, forget conventions, ignore security, and silently ship technical debt. aiZee forces them to read from a centralized source of truth *before* writing a single line.

| Without aiZee | With aiZee |
| :--- | :--- |
| Context drift after a few prompts | Rules + personas hard-loaded every session |
| Deprecated packages, silent tech debt | Exact-version tech-stack locked via live MCP docs |
| Raw SQL, missing XSS, weak secrets | OWASP, zero-trust, RBAC enforced by default |
| Random drive-by refactoring | Surgical changes through policy + budget + audit gates |
| One-size-fits-all AI answers | 20 personas + 66 skills auto-selected per task |

---

## Quick Start

### Prerequisites

| Requirement | Minimum | Recommended |
| :--- | :--- | :--- |
| Python | 3.10 | 3.12 |
| Git | 2.30+ | Latest |
| OS | Windows 10 / macOS 12 / Ubuntu 22.04 | Latest |

### Installation

```bash
git clone https://github.com/m3taz-ahmed/ai-globals.git .ai
cd .ai
```

**Windows — GUI wizard** (double-click `install.bat` or run):
```powershell
.\install.ps1 -Gui
```

**Windows — CLI:**
```powershell
.\install.ps1
```

**macOS / Linux:**
```bash
bash install.sh
```

### Verify

```bash
aizee doctor    # Health check
aizee status    # Current persona, skills, budget
```

---

## Core Architecture

```
.ai/                         # Sovereign root (discovered via AIZEE_ROOT)
├── AGENTS.md                # Cross-tool canonical bootloader
├── global-roles.md          # 20 personas + operational rules
├── global-workflow.md       # Cognitive loading & execution protocol
├── runtime/                 # Kernel: policy, budget, audit, 63+ modules
├── memory/                  # SQLite + FTS5 + vector memory service
├── aizee_mcp/                # MCP server (27 tools, 3 resources)
├── eval/                    # Agent benchmark & eval harness
├── skills/                  # 66 persona + lord skill files
├── workflows/               # 31 trigger-based execution protocols
├── rules/                   # Compressed behavioral rules
├── tech-stack/              # Version-locked stack references
├── dashboard/               # Web dashboard (Python stdlib HTTP)
├── scripts/                 # Installers, validators, MCP wrappers
├── install.ps1 / install.sh # Idempotent OS installer
└── pyproject.toml           # Package metadata + quality config
```

---

## The Six Pillars

### 1. Persona + Skill Composition
20 personas (`ARCH`, `QA`, `SEC`, `DEV`, `SRE`, `DATA`, `ML`, `DEVOPS`, `API`, `FREELANCE`, etc.) with 13 lord-level domain skills. Auto-detected per task — no manual selection needed.

```bash
aizee persona detect --multi "build a secure docker API with postgres"
# → Primary: ARCH + Secondary: SEC, DEVOPS + Lords: security-lord, cloud-platforms-lord
```

### 2. Runtime Governance
Every action passes through a 5-gate pipeline before execution:

```
Probity → Guardian → Policy → Budget → Audit
```

- **Policy engine** — `allow/ask/deny` YAML rules with AST-safe evaluation
- **Budget manager** — token/cost/call limits per session/hour/day/week/month
- **Audit logger** — SHA-256 hash-chained, tamper-evident trail
- **Workflow runner** — durable SQLite-backed execution with saga support

### 3. Live Ground-Truth
Context7 MCP fetches current library docs before implementation. Graphify knowledge graph replaces blind `grep` for codebase navigation.

### 4. Hybrid Memory
SQLite + FTS5 full-text search + optional vector indexing (SentenceTransformers). Episodic, semantic, factual, and procedural memory layers.

```bash
aizee memory ingest          # Rebuild index after changes
aizee memory search "docker" # Full-text + vector search
```

### 5. Quality Gates (Zero Defect)
```bash
ruff check .                 # 0 warnings
mypy                         # Strict typing, 90+ files
pytest -q                    # 2343 tests, 91% coverage
python eval/harness.py       # E2E eval: ruff + mypy + pytest + validate-globals
```

### 6. Token Efficiency
Persona detection is local (pure Python, zero LLM tokens). Only relevant skill names are returned — not full files. Default limits: 1 primary persona + 4 secondary + 5 lord skills.

---

## What's New in v5.0.0

### 18 Original Features

From competitive analysis of AI agent OS and coding governance tools:

| Feature | Module | Purpose |
| :--- | :--- | :--- |
| Hash-chained audit log | `runtime/audit.py` | Tamper-evident action trail |
| AST validation | `runtime/ast_validator.py` | Plan/diff validation before & after edits |
| Agent benchmark engine | `eval/agent_benchmark.py` | Persona performance scoring |
| OWASP Agentic Top 10 | `runtime/agentic_security.py` | 10 security controls for agentic systems |
| MCP security scanner | `runtime/mcp_security.py` | Static analysis for MCP servers & skills |
| Skills marketplace | `runtime/skills_marketplace.py` | Community skill registry with security scanning |
| AI code review engine | `runtime/review_engine.py` | Multi-dimensional review with confidence scoring |
| Git-backed memory | `memory/git_memory.py` | Versioned memory with git branches per persona |
| Code compression | `runtime/code_compressor.py` | AST-based ~70% token reduction |
| OpenTelemetry exporter | `runtime/otel_exporter.py` | OTLP/JSON trace export with fallback |
| Parallel agents | `runtime/worktree_pool.py` | Git worktree-based parallel execution |
| Spec-driven development | `runtime/spec_engine.py` | 4-phase: Specify → Plan → Tasks → Implement |
| Dynamic personas | `runtime/dynamic_persona.py` | 3-layer evolution with experience tracking |
| Issue tracker integration | `runtime/issue_tracker.py` | Linear/Jira/Notion unified client |
| Command Center | `runtime/command_center.py` | Fleet management Kanban dashboard |
| AI slop detector | `runtime/ai_slop_detector.py` | Detects AI-generated code quality issues |
| Voice interface | `runtime/voice_interface.py` | Cross-platform STT/TTS |
| ACP protocol | `runtime/acp_protocol.py` | Inter-agent communication broker |

### 45 New Enhancements (Repo Research Driven)

Deep analysis of 22 GitHub repositories (agent-governance-toolkit, OpenMemory, metis, spec-kit, open-code-review, agent-policy-engine, sol sentinel, caracal, ouroboros, and more) yielded 45 enhancements across 3 phases:

#### Phase 1 — High-Impact, Low-Complexity (12 features)

| Feature | Module | Source |
| :--- | :--- | :--- |
| Parameterized policy conditions | `runtime/authorization.py` | DAE Standard |
| Lease generation (fencing token) | `runtime/authorization.py` | agent-policy-engine |
| 3 enforcement modes (DISABLED/OBSERVE/ENFORCE) | `runtime/authorization.py` | agent-policy-engine |
| 5-gate evidence-based evaluation | `eval/harness.py` | agentic-os |
| Single-writer atomic file locking | `runtime/file_lock.py` | agentic-os |
| SimHash deduplication | `memory/simhash.py` | OpenMemory |
| Heat-based memory prioritization | `memory/heat.py` | MemoryOS |
| Stall detection (output hashing) | `runtime/worktree_pool.py` | sol sentinel |
| Tether files (crash recovery) | `runtime/worktree_pool.py` | sol |
| 5-gate deterministic file filter | `runtime/review_engine.py` | open-code-review |
| Hash-tracked spec manifests | `runtime/spec_engine.py` | spec-kit |
| Delta-based specs (ADDED/MODIFIED/REMOVED) | `runtime/spec_engine.py` | OpenSpec |

#### Phase 2 — Medium-Impact, Medium-Complexity (18 features)

| Feature | Module | Source |
| :--- | :--- | :--- |
| Execution rings (4 privilege levels) | `runtime/execution_rings.py` | agent-governance-toolkit |
| 3-stage evaluation gate | `eval/stages.py` | ouroboros |
| Saga compensation (multi-step rollback) | `runtime/saga_compensation.py` | agent-governance-toolkit |
| Memory consolidation primitives | `memory/consolidation.py` | agent-memory |
| 5 cognitive sector classification | `memory/sectors.py` | OpenMemory HMD v2 |
| Temporal knowledge graph | `memory/temporal.py` | OpenMemory |
| 3-mode delegation (inherit/narrow/none) | `runtime/authorization.py` | caracal |
| Runtime state machine | `runtime/authorization.py` | agent-policy-engine |
| Provenance tracking | `runtime/authorization.py` | agent-policy-engine |
| Three-zone memory compression | `runtime/memory_compression.py` | open-code-review |
| CodeGraph builder (AST-based) | `runtime/codegraph.py` | metis |
| CodeGraph reachability analysis | `runtime/codegraph.py` | metis |
| Budget rate limiting (token bucket) | `runtime/rate_limiter.py` | agent-governance-toolkit |
| Self-healing runtime (crash recovery) | `runtime/self_healing.py` | sol sentinel |
| Spec constitution validation | `runtime/spec_validation.py` | spec-kit |
| Spec test scenarios (Gherkin) | `runtime/spec_validation.py` | spec-kit |
| Spec linkage graph (impact analysis) | `runtime/spec_validation.py` | spec-kit |
| Fuzz testing harness | `runtime/fuzz_testing.py` | agent-policy-engine |

#### Phase 3 — High-Impact, High-Complexity (15 features)

| Feature | Module | Source |
| :--- | :--- | :--- |
| Tree-sitter symbol provider | `runtime/tree_sitter_provider.py` | metis |
| Diff-based code review | `runtime/diff_review.py` | open-code-review |
| Budget anomaly detection (z-score) | `runtime/budget_anomaly.py` | agent-governance-toolkit |
| Policy decision caching (TTL) | `runtime/policy_cache.py` | agent-policy-engine |
| Memory decay scheduler | `memory/decay_scheduler.py` | OpenMemory |
| Semantic code search (TF-IDF) | `runtime/semantic_search.py` | metis |

---

## CLI Reference

```bash
aizee status                         # OS health + counts
aizee doctor                         # Full diagnostic
aizee persona detect --multi "task"  # Detect personas for a task
aizee check edit --args '{"tokens":100}'  # Policy + budget gate
aizee run 02-execution               # Run a workflow
aizee memory ingest                  # Rebuild memory index
aizee memory search "query"          # Search memory
aizee skill list                     # List available skills
aizee skill search security          # Search skills by keyword
aizee mcp context7 resolve-library-id --args '{"library":"fastapi"}'
aizee graphify                       # Build knowledge graph
aizee test                           # Fast test tier (~10s)
aizee test --full                    # Full suite with coverage
aizee uninstall                      # Interactive uninstall (keeps learned data)
aizee uninstall --gui                # GUI uninstaller (tkinter)
aizee perf                           # Performance benchmarks
```

### One-Click Scripts (Windows .bat)

| Script | Description |
| :--- | :--- |
| `install.bat` | GUI installer (double-click) |
| `update.bat` | Pull latest from GitHub + re-run post-install hooks |
| `backup.bat` | Backup learned data (memory/state/brain/graph/.env) to timestamped folder |
| `restore.bat` | Auto-merge learned data from backups (smart checkpoint) |
| `restore.bat --from PATH` | Full restore from specific backup (overwrite) |
| `restore.bat --list` | List available backups |
| `restore.bat --checkpoint` | Show current restore checkpoint |
| `uninstall.bat` | GUI uninstaller (double-click) |

---

## Connect to Your AI Agent

| AI tool | Config file |
| :--- | :--- |
| Cursor | `.cursor/rules/aizee.mdc` |
| Claude Code | `.claude/CLAUDE.md` |
| Windsurf | `.windsurfrules` |
| Cline | `.clinerules/aizee.md` |
| Aider | `.aider.conf.yml` |
| GitHub Copilot | `.github/copilot-instructions.md` |
| Devin | `.devin/skills/global-os/SKILL.md` |
| Any other | Load `AGENTS.md` + `global-roles.md` + `global-workflow.md` |

The installer auto-symlinks these to the correct global locations.

---

## MCP Servers

7 MCP servers configured automatically:

| Server | Purpose | Requires |
| :--- | :--- | :--- |
| `aizee` | Core OS tools (27 tools) | Python |
| `graphify` | Codebase knowledge graph | Python + graphify |
| `context7` | Live library documentation | Node.js 18+ |
| `upwork` | Upwork job search + proposals | Node.js + OAuth |
| `freelancer` | Freelancer project bidding | Node.js + OAuth |
| `fiverr` | Fiverr gig search | uvx |
| `linkedin` | LinkedIn content automation | Python + OAuth |

Secrets are centralized in `.env` (git-ignored). Copy `.env.example` and fill in credentials.

---

## GUI Installer

A full **WPF wizard** with 8 pages, dark theme, live progress, and `.env` secrets management.

**Double-click launch** (Windows): just run `install.bat` — no terminal needed.

**From terminal:**
```powershell
.\install.ps1 -Gui                              # Launch wizard
.\installer\gui_installer.ps1 -Silent           # Silent (no GUI)
.\installer\gui_installer.ps1 -InstallDir D:\x  # Pre-set location
```

| Page | What it does |
| :--- | :--- |
| Welcome | Version, license, 6-step overview |
| License | MIT license + accept checkbox |
| Location | In-place or custom path + disk space |
| Components | 27 checkboxes across 5 sections |
| Configuration | Env vars, scope, install options |
| Pre-flight | 7 system checks + .env secrets check |
| Progress | Live progress bar + scrolling log |
| Finish | Summary + launch dashboard / open .env |

---

## Dashboard

```bash
python dashboard/server.py 8080
# → http://127.0.0.1:8080
```

Dark-first command-center UI: command palette (`Ctrl+K`), bento-grid metrics, status pills, glass panels. Optional Bearer auth via `AGENT_OS_DASHBOARD_TOKEN`.

---

## Quality Gates

| Gate | Command | Status |
| :--- | :--- | :--- |
| Lint | `ruff check .` | 0 warnings |
| Types | `mypy` | 0 errors (90+ files, strict) |
| Tests (fast) | `aizee test` | 2100+ passed, ~12s |
| Tests (full) | `aizee test --full` | 2343 passed, 91% coverage, ~100s |
| Integrity | `scripts/validate-globals.py` | 0 errors |
| E2E | `python eval/harness.py` | all_pass: true |

---

## Tech Stack

- **Core:** Pure Python 3.10+ (no Node.js required for core OS)
- **Memory:** SQLite + FTS5 + optional SentenceTransformers vectors
- **MCP:** FastMCP server with 27 tools
- **Dashboard:** Python stdlib HTTP server + SQLite
- **Knowledge graph:** graphify (optional)
- **Dependencies:** pyyaml, pydantic, rich, cryptography, numpy, turbovec

---

## Contributing

1. Fork → feature branch (`feature/*`)
2. Write tests first (AAA pattern, one behavior per test)
3. Run `ruff check . && mypy && pytest -q && python eval/harness.py`
4. All gates must pass — no PR without green
5. Conventional commits: `type(scope): subject`
6. PR ≤ 400 lines, targeted tests only

---

## License

MIT — see [LICENSE](LICENSE).

---

<div align="center">
  <p><strong>aiZee</strong> — The policy layer for AI coding.</p>
  <p>Built by <a href="https://linkedin.com/in/moataz-ahmed">Moataz Ahmed</a></p>
</div>
