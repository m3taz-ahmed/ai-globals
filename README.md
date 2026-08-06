<div align="center">
  <img src="logo.png" width="160" alt="AI Global OS Logo">
  <h1>AI Global OS</h1>
  <p><strong>Stop letting AI write spaghetti code. Turn it into your Principal Architect.</strong></p>

  <p>
    <img src="https://img.shields.io/badge/Version-4.22.0-6C63FF?style=for-the-badge&logo=buffer&logoColor=white&labelColor=1a1a2e" alt="Version 4.22.0">
    <img src="https://img.shields.io/badge/Status-Self--Healing-00C896?style=for-the-badge&logo=dependabot&logoColor=white&labelColor=1a1a2e" alt="Status: Self-Healing">
    <img src="https://img.shields.io/badge/Architecture-Sovereign-F59E0B?style=for-the-badge&logo=moleculer&logoColor=white&labelColor=1a1a2e" alt="Architecture: Sovereign">
    <img src="https://img.shields.io/badge/License-MIT-3B82F6?style=for-the-badge&logo=opensourceinitiative&logoColor=white&labelColor=1a1a2e" alt="License: MIT">
  </p>
  <p>
    <img src="https://img.shields.io/badge/Personas-19%20Roles-EC4899?style=for-the-badge&logo=buffer&logoColor=white&labelColor=1a1a2e" alt="19 Personas">
    <img src="https://img.shields.io/badge/Skills-73%20Specialized-10B981?style=for-the-badge&logo=checkmarx&logoColor=white&labelColor=1a1a2e" alt="73 Skills">
    <img src="https://img.shields.io/badge/Workflows-29%20Durable-0EA5E9?style=for-the-badge&logo=checkmarx&logoColor=white&labelColor=1a1a2e" alt="29 Workflows">
  </p>

  <p><i>A zero-compromise, version-controlled operating system that eliminates AI context drift, enforces bleeding-edge engineering standards, and governs every line of generated code.</i></p>
</div>

---

[Read this in Arabic](README-AR.md)

---

## Table of Contents

1. [Why use AI Global OS?](#why-use-ai-global-os)
2. [What you need before you start](#what-you-need-before-you-start)
3. [Activate in 60 seconds](#activate-in-60-seconds)
4. [The six pillars of AI Global OS](#the-six-pillars-of-ai-global-os)
5. [Dashboard and observability](#dashboard-and-observability)
6. [System architecture](#system-architecture)
7. [For non-programmers: what this means for your team](#for-non-programmers-what-this-means-for-your-team)
8. [Connect the OS to your AI agent](#connect-the-os-to-your-ai-agent)
9. [Global rules to paste into your AI agent IDE](#global-rules-to-paste-into-your-ai-agent-ide)
10. [CLI reference](#cli-reference)
11. [The 19 personas and 13 lord skill domains](#the-19-personas-and-13-lord-skill-domains)
12. [Workflows](#workflows)
13. [Recent highlights and new features](#recent-highlights-and-new-features)
14. [Quality gates and contributing](#quality-gates-and-contributing)

---

## Why use AI Global OS?

Most teams use AI as a high-speed junior developer. It writes fast, but it hallucinates APIs, forgets naming conventions, ignores N+1 queries, and silently ships technical debt.

**AI Global OS** is a Sovereign Architectural Engine. It forces Cursor, Copilot, Claude, Gemini, Windsurf, Cline, Aider, and GitHub Copilot to read from a centralized, version-controlled source of truth *before* writing a single line of code.

| Without AI Global OS | With AI Global OS |
| :--- | :--- |
| Context drift after a few prompts | Rules and personas hard-loaded every session |
| Deprecated packages and silent tech debt | Exact-version tech-stack locked via live MCP docs |
| Raw SQL, missing XSS filters, weak secrets | OWASP, zero-trust, and RBAC enforced by default |
| Random drive-by refactoring | Surgical changes through policy, budget, and audit gates |
| One-size-fits-all AI answers | The right persona(s) and domain skills for the task |

---

## What you need before you start

| Requirement | Minimum | Recommended |
| :--- | :--- | :--- |
| **Python** | 3.10 | 3.11 or 3.12 |
| **pip** | Latest | Latest |
| **Git** | 2.30+ | Latest |
| **OS** | Windows 10 / macOS 12 / Linux (glibc 2.31+) | Windows 11 / macOS 14 / Ubuntu 22.04+ |

Optional but strongly recommended:

- A compatible AI coding assistant: **Cursor**, **GitHub Copilot**, **Claude Code**, **Windsurf**, **Cline**, **Aider**, or similar.
- **Context7 MCP** for live, version-correct library documentation.
- **graphify** knowledge graph (built from the repo itself, no LLM required).

The core OS is **pure Python**. Node.js is only needed if you extend the dashboard/frontend; the built-in dashboard runs on Python's standard-library HTTP server and SQLite.

---

## Activate in 60 seconds

> Make sure **Python 3.10+** and **Git** are installed. The OS itself is pure Python; Node.js is only needed if you extend the dashboard/frontend.

1. **Clone the central brain** to a fixed location (for example `D:/.ai` or `~/.ai`):
   ```bash
   git clone https://github.com/m3taz-ahmed/ai-globals.git D:/.ai
   ```

2. **Install the OS**:
   ```powershell
   # Windows
   .\install.ps1

   # macOS / Linux
   bash install.sh
   ```
   The installer copies the repo to your OS root, installs the `aios` package with `[dev,graphify]` extras, builds the integrity manifest, and creates the `ai-os` CLI shim.

3. **Install Python dependencies** inside the cloned folder (only needed if you skipped the installer):
   ```bash
   python -m pip install -e '.[graphify]'
   ```
   For development (tests, linting, graph), use `'.[dev,graphify]'`.

4. **Verify the installation**:
   ```bash
   ai-os doctor
   ai-os status
   ```
   `doctor` checks that the OS root, policies, rules, and vector index are healthy. `status` prints the current persona, skill, workflow, and budget counts.

5. **Use the CLI**:
   ```bash
   ai-os persona detect --multi "your task description"
   ai-os check edit
   ai-os run 02-execution
   ai-os memory ingest
   ```

6. **Start the local dashboard** (optional):
   ```bash
   python dashboard/server.py 8080
   ```
   Then open `http://127.0.0.1:8080`. Set `AGENT_OS_DASHBOARD_TOKEN` to require Bearer authentication.

7. **Enable the MCP server**:
   Add `aios_mcp/config.json` to your IDE MCP config, or run:
   ```bash
   python aios_mcp/aios_server.py
   ```

8. **Point your AI agent at the OS rules**:
   See [Connect the OS to your AI agent](#connect-the-os-to-your-ai-agent) for the exact file to load into Cursor, Copilot, Claude, Windsurf, Cline, or Aider.

Your AI is now sovereign. It analyzes every request against SOLID, OWASP, WCAG, and your exact tech stack before generating code.

---

## The six pillars of AI Global OS

AI Global OS is not a prompt library. It is a runtime control plane that sits between you and every AI agent you use.

### 1. Persona + Lord Skill composition

The OS ships with **19 personas** (from `ARCH` to `CV`) and **13 lord-level domain skills**. For every request the OS detects the most relevant persona *set* and loads the matching skill files. You can also spawn agents with multiple personas, e.g. `ARCH + QA + security-lord`.

```bash
ai-os persona detect --multi "build a secure docker API with postgres"
# Returns primary persona, secondary personas, primary skills, and lord skills.
```

This is implemented in `runtime/persona.py` + `runtime/skill_resolver.py` and used by `Kernel`, `WorkflowRunner`, and `AgentPool`.

**New:** skills and rules can declare YAML frontmatter that makes them active only for specific paths, stacks, or persona combinations. The runtime filters skills automatically, so an agent never receives irrelevant guidance.

### 2. Runtime governance

Every action passes through a policy + budget gate before it runs.

- **Policy engine** — `allow/ask/deny` YAML rules with safe AST evaluation.
- **Budget manager** — token/cost/call limits per scope.
- **Audit logger** — every decision is recorded.
- **Workflow runner** — durable SQLite-backed execution with saga support.
- **Saga orchestrator** — compensating actions for long-running operations.
- **Telemetry** — structured events for observability.

**New:** `Kernel.act`, `run_workflow`, `chat_message`, and `run_saga` accept a `fresh_context` parameter. When enabled, the kernel resets the per-session budget and re-derives persona/skill keys so a new chat or workflow cannot inherit stale auto-injected context.

### 3. Live ground-truth, not stale memory

Before implementing any external library or framework, the OS queries Context7 MCP (`resolve-library-id` then `get-library-docs`) so the generated code matches the actual current API. If `graphify-out/graph.json` exists, the OS navigates the knowledge graph instead of blind `grep`.

You can also query these tools from the CLI:

```bash
# List your skills
ai-os skill list

# Read a skill
ai-os skill invoke technical-writer

# Search skills by keyword
ai-os skill search security

# Call an external MCP tool
ai-os mcp context7 resolve-library-id --args '{"library":"fastapi"}'
```

### 4. Memory you can trust

The memory service uses SQLite + FTS5 plus optional vector indexing. It stores episodic, semantic, factual, and procedural context. After every rule, tech-stack, or workflow change, `ai-os memory ingest` refreshes the index.

```bash
ai-os memory ingest
ai-os memory search "docker deployment"
ai-os query "auth pattern"
```

### 5. Engineering standards enforced by code

Quality is not optional. The built-in CI pipeline and `python eval/harness.py` run:

- `ruff check .` for lint.
- `mypy` for strict typing.
- `pytest -q` for tests.
- `scripts/validate-globals.py --fix` for integrity.

The OS forbids raw SQL interpolation, `any` type abuse, inline imports, wildcard CORS, and unvalidated destructive actions.

### 6. Token efficiency (negligible context cost)

The OS is designed to add as few tokens as possible to the AI context window — **you do not need to type any special flags**. The defaults already keep the context small:

- **Persona detection is local** — pure Python string scoring, no LLM call, zero tokens.
- **Only skill names are returned by default** — the runtime does not dump every skill file into the prompt.
- **Tight limits by default**: 1 primary persona skill + up to `max_personas - 1` secondary skills + up to `max_lords` (default **5**) lord skills.
- The flags below are only for power users or CI scripts that want to cap context explicitly:

  ```bash
  # Keep it tiny (single persona, no lords)
  ai-os persona detect --multi "deploy docker" --max-personas 1 --max-lords 0 --single

  # Allow a small panel
  ai-os persona detect --multi "..." --max-personas 2 --max-lords 3
  ```

- `Kernel.act`, `WorkflowRunner`, and `AgentPool` all respect these limits, so an agent spawned with `ARCH + QA + security-lord` only loads the files that are actually relevant.

---

## Dashboard and observability

The AI Global OS dashboard is a dark-first, command-center-style web UI for monitoring and operating the OS. It is not a marketing page; it is an operational cockpit where you can see personas, runtime state, budget, memory, skills, graphify, and telemetry in one place.

Key features (defined in `DESIGN.md`):

- **Command palette** — press `Cmd/Ctrl + K` to open a global command palette.
- **Bento-grid metric cards** — active sessions, tokens used, memory hit rate, graphify nodes, pending skills, last audit.
- **Status pills** — green for allowed/completed, amber for warnings, red for blocked/denied.
- **Glass panels** and a deep lapis-charcoal color system with cyan (AI state), violet (knowledge), and lime (success) accents.
- **Security** — configurable CORS allow-list, CSRF header checks, request-size limits, and optional `AGENT_OS_DASHBOARD_TOKEN` Bearer auth.

Start it with:

```bash
python dashboard/server.py 8080
```

---

## System architecture

```text
.ai/                              # Sovereign root
├── AGENTS.md                     # Cross-tool canonical instruction
├── global-roles.md               # [Layer 0] Personas and identity
├── global-roles-ar.md            # [Layer 0] Arabic persona charter
├── global-workflow.md            # [Core] Cognitive loading & execution protocol
├── README.md                     # Human front door (this file)
├── README-AR.md                  # Arabic front door
├── Memory.md                     # Short-term cross-session context
├── state/CHANGELOG.md            # Release notes
│
├── .cursor/rules/                # Cursor rule adapters
├── .claude/                      # Claude Code config, skills, agents
├── .clinerules/                  # Cline rules
├── .windsurfrules                # Windsurf rules
├── .aider.conf.yml               # Aider config
├── .github/copilot-instructions.md # GitHub Copilot instructions
├── .devin/skills/global-os/      # Devin skill adapter
├── .windsurf/skills/global-os/   # Windsurf skill adapter
│
├── rules/                        # Compressed behavioral & structural rules
├── tech-stack/                   # Compressed domain-specific RAG tech-stacks
├── workflows/                    # Compressed trigger-based execution protocols
├── skills/                       # Persona + lord skill files
│
├── state/                        # Logs & persistent state
├── brain/                        # Memory database
├── graphify-out/                 # Knowledge graph
│
├── runtime/                      # Runtime kernel (policy, budget, workflow, chat, telemetry)
├── memory/                       # Memory service
├── aios_mcp/                     # MCP server
├── dashboard/                    # Web dashboard
├── cli.py                        # CLI entry point
├── config.py                     # Root discovery
├── install.ps1 / install.sh      # OS installer
├── plugins.yaml                  # Plugin manifest
├── pyproject.toml                # Package metadata
└── scripts/                      # Self-healing operations
    ├── validate-globals.py       # Integrity validator
    ├── sync-agent-configs.py     # Sync configs across tools
    └── graphify_mcp_wrapper.py   # Graphify MCP bridge
```

---

## For non-programmers: what this means for your team

**The short version:** AI Global OS turns chaotic AI-assisted coding into a disciplined, repeatable process that protects quality and reduces risk.

- **No more "the AI forgot what we agreed on."** Every session reloads the same rules, standards, and project context.
- **No more guessing if the code is safe.** Security, performance, and compliance checks are built in, not optional.
- **No more one AI personality for everything.** The OS chooses the right expert — or team of experts — for the job, whether that is an architect, a security auditor, a data engineer, or a technical writer.
- **No more silent technical debt.** Every change is audited, budgeted, and validated before it is accepted.
- **It works with the tools you already use.** Cursor, Copilot, Claude, Gemini, Windsurf, Cline, Aider, and GitHub Copilot all read the same rulebook.

Think of AI Global OS as the "policy and training layer" that makes every AI assistant behave like a senior member of your engineering team.

---

## Connect the OS to your AI agent

After cloning, tell your AI coding tool to read the OS rules. Each tool has its own adapter file:

| AI tool | File to load / copy into project instructions |
| :--- | :--- |
| **Cursor** | `.cursor/rules/ai-global-os.mdc` |
| **Claude Code / Claude projects** | `.claude/CLAUDE.md` |
| **Windsurf** | `.windsurfrules` (auto-loaded if in project root) |
| **Cline** | `.clinerules/ai-global-os.md` |
| **Aider** | `.aider.conf.yml` |
| **GitHub Copilot (in-repo)** | `.github/copilot-instructions.md` |
| **Devin** | `.devin/skills/global-os/SKILL.md` |
| **Any other agent** | Load `AGENTS.md` + `global-roles.md` + `global-workflow.md` into the system prompt / project instructions. |

The fastest generic setup is to point the agent at:

```text
AGENTS.md
global-roles.md
global-workflow.md
```

These three files give the agent the identity, rules, and execution protocol. The `skills/` and `tech-stack/` files are loaded on demand by the runtime, so they are not copied into the prompt window by hand.

---

## Global rules to paste into your AI agent IDE

If your IDE has a **global / user-level rules** or **system instructions** field (Cursor *User Rules*, Windsurf *Global Rules*, Claude *Project Instructions*, etc.), paste the block below. It teaches every AI session how to boot from AI Global OS.

```text
You are an AI Global OS agent. The OS root is discovered from the `AGENT_OS_ROOT` environment variable or the install directory (`D:/.ai`, `~/.ai`, etc.).

MUST on every session:

1. Cold start: read `global-roles.md` then `global-workflow.md` from the OS root. NEVER trust cached context.
2. Detect the user's persona:
   - For single-domain tasks: `ai-os persona detect "<user prompt>"`.
   - For multi-domain tasks: `ai-os persona detect --multi "<user prompt>"`.
   - Adopt the returned persona(s) and primary skill(s) for the whole session.
3. If the current project has a `spec.md`, read it before any action.

MUST before loading context:

4. Lazy context layers (do not dump all files at once):
   - L0: `rules/core-behavioral-compact.md` + `skills/<primary-skill>/SKILL.md` + any lord skills returned by persona detection.
   - L1: `rules/vocabulary.md`, `rules/anti-patterns.md`, `tech-stack/useful-repos.md`.
   - L2: matched `rules/*.md` + `tech-stack/<pkg>-<ver>.md`.
   - L3: `workflows/<id>.md` for the current task.
5. VersionGate: before loading any `tech-stack/` file, read `composer.lock`, `package-lock.json`, `composer.json`, or `package.json` and load only the matching version.
6. Before implementing any external library/framework, query Context7 MCP (`resolve-library-id` then `get-library-docs`). Never rely on memory.
7. If `graphify-out/graph.json` exists, use `graphify query` or MCP `query_graph` instead of raw grep.

MUST for execution:

8. Route every tool/action through `runtime/kernel.py`: use `ai-os check <action> --args` or `Kernel.act`. No destructive action without explicit user approval.
9. Check `runtime/budget` before every LLM call. Stop on hard cap.
10. Prefer the native MCP server (`aios_mcp/aios_server.py`) for `query_rules`, `check_policy`, `search_memory`, and `search_memory_vector`.

MUST for quality:

11. Run `ruff check .`, `mypy`, `pytest -q`, and `python eval/harness.py` before declaring done.
12. After changing `rules/`, `tech-stack/`, `workflows/`, or `skills/`, run `ai-os memory ingest` and `graphify update .`.
13. Git: conventional commits, atomic, never `git add .` (`[GIT-06]`) or force push, stage only files you modified.
```

For **project-level** rules, use the adapter files in the table above instead.

---

## CLI reference

The `ai-os` command is the primary interface to the OS. All commands support `--root` and `--project` to override the discovered OS and project roots.

| Command | Purpose | Example |
| :--- | :--- | :--- |
| `status` | Show OS root, persona, skill, workflow, budget, and rule counts. | `ai-os status` |
| `doctor` | Check that the environment is healthy. | `ai-os doctor` |
| `version` | Print the OS version. | `ai-os version` |
| `sync` | Sync agent configs across tools. | `ai-os sync` |
| `persona detect` | Detect the best persona(s) for a task. | `ai-os persona detect --multi "secure API"` |
| `persona list` | List all personas. | `ai-os persona list` |
| `skill list` | List available skills. | `ai-os skill list` |
| `skill invoke` | Display a skill's markdown content. | `ai-os skill invoke database-lord` |
| `skill search` | Search skills by keyword. | `ai-os skill search mariadb` |
| `check` | Ask the policy engine if an action is allowed. | `ai-os check edit --args '{"file":"x.py"}'` |
| `policy test` | Dry-run a policy decision. | `ai-os policy test edit --args '{"file":"x.py"}'` |
| `run` | Execute a durable markdown workflow. | `ai-os run 02-execution` |
| `saga` | Run a saga with compensations. | `ai-os saga my-saga --steps '[...]'` |
| `query` | Hybrid search across memory. | `ai-os query "auth pattern"` |
| `memory search` | Search memory by kind. | `ai-os memory search "docker"` |
| `memory ingest` | Re-ingest rules, skills, and workflows. | `ai-os memory ingest` |
| `budget list` | Show configured budgets. | `ai-os budget list` |
| `budget set` | Update a budget. | `ai-os budget set --scope global --max-tokens 100000` |
| `project init` | Scaffold a new project with OS structure. | `ai-os project init --path ./my-project` |
| `agent spawn` | Spawn a sub-agent with a persona. | `ai-os agent spawn --persona ARCH,QA --agent-id worker-1` |
| `agent list` | List active agents. | `ai-os agent list` |
| `chat` | Persistent chat REPL or one-shot message. | `ai-os chat "hello"` |
| `ci` | Run the built-in CI quality gates. | `ai-os ci` |
| `stack detect` | Detect the tech stack of the current project. | `ai-os stack detect` |
| `stack show` | Show loaded tech-stack docs. | `ai-os stack show` |
| `mcp` | Call an external MCP tool. | `ai-os mcp context7 resolve-library-id --args '{"library":"fastapi"}'` |
| `telemetry summary` | Show telemetry summary. | `ai-os telemetry summary` |
| `graphify` | Rebuild the knowledge graph. | `ai-os graphify` |

Run `ai-os --help` for the full list and `ai-os <command> --help` for command-specific options.

---

## The 19 personas and 13 lord skill domains

Personas shape **who** the AI acts like. Lord skills add **deep domain knowledge** on demand.

| Persona | Focus | Primary skill |
| :--- | :--- | :--- |
| **ARCH** | Chief architect, system design, rapid prototyping | `ai-agents-architect` |
| **QA** | Testing, coverage, edge cases, regression hunting | `qa-debugger` |
| **UX** | UI/UX, design systems, accessibility, motion | `frontend-ui-expert` |
| **DEV** | Master developer, backend, APIs, clean code | `backend-api-expert` |
| **SRE** | Reliability, observability, chaos engineering, cloud | `sre` |
| **SEC** | Security, zero-trust, Linux kernel, audits | `security-auditor` |
| **GAME** | 60 FPS game loops, rendering, cross-platform | `game-architect` |
| **PLAY** | Google Play, Android publishing, IAP, ASO | `google-play-warlord` |
| **MOBILE** | Mobile games/apps, Fastlane, anti-cheat | `mobile-game-producer` |
| **DATA** | ETL, data modeling, databases, pipelines | `data-engineer` |
| **ML** | Machine learning, LLMs, inference, MLOps | `ml-engineer` |
| **DEVOPS** | CI/CD, containers, GitOps, release automation | `devops-engineer` |
| **API** | API design, REST/GraphQL, microservices, integrations | `api-architect` |
| **LEGAL** | Privacy, compliance, licensing, audits | `legal-compliance` |
| **PRODUCT** | Requirements, roadmaps, prioritization, metrics | `product-manager` |
| **DOC** | READMEs, API docs, runbooks, changelogs | `technical-writer` |
| **PERF** | Latency, throughput, profiling, optimization | `performance-engineer` |
| **PROPOSAL** | Proposals, bids, Arabic/English client copy | `proposal-writer` |
| **CV** | ATS-optimized resumes, LinkedIn, cover letters | `cv-writer` |

Lord skill domains: `database-lord`, `mariadb-lord`, `ai-ml-lord`, `devops-lord`, `cloud-platforms-lord`, `frontend-frameworks-lord`, `backend-frameworks-lord`, `page-sections-lord`, `language-lord`, `linux-systems-lord`, `messaging-streaming-lord`, `search-vector-lord`, `security-lord`.

When a prompt touches multiple domains, the OS composes a panel — for example `DEV + API + security-lord` — and loads the union of relevant skill files.

---

## Workflows

Workflows are durable, markdown-driven execution protocols stored in `workflows/`. They are backed by SQLite, support checkpoints, and can be triggered from the CLI or by the agent.

Core execution workflows:

| ID | Purpose |
| :--- | :--- |
| `00-prompt-architecting` | Refine and architect a user prompt. |
| `01-planning` | Plan a feature or task end-to-end. |
| `02-execution` | Execute a planned task. |
| `03-debugging` | Debug a failing system. |
| `04-deployment` | Deploy to production safely. |
| `05-code-review` | Review code against standards. |
| `06-maintenance` | Run recurring maintenance. |
| `07-security-audit` | Audit for security issues. |
| `08-onboarding` | Onboard a new project or developer. |
| `09-discovery` | Explore an unfamiliar codebase. |
| `10-saga-reconciliation` | Reconcile a failed saga. |
| `11-audit-core` | Core audit checklist. |
| `12-audit-ui` | UI/UX audit checklist. |
| `13-audit-perf` | Performance audit checklist. |
| `14-ponytail-review` | Technical-debt review. |
| `15-page-builder-setup` | Scaffold a section-based page builder. |
| `16-cleanup-and-scm` | Clean up and stage changes. |
| `17-memory-sync` | Sync memory after a milestone. |

Run any workflow with:

```bash
ai-os run 02-execution
```

---

## Recent highlights and new features

### v4.22.0

- **19 personas and 73 specialized skills**, including the new `PROPOSAL` and `CV` personas, and **29 durable workflows**.
- **Multi-persona + lord skill composition** via `PersonaDetector.detect_multiple`, `SkillResolver`, and `Kernel`/`WorkflowRunner`/`AgentPool` integration.
- **Externalized persona definitions** in `runtime/personas.yaml` so persona wiring can be updated without touching code.
- **Clean Architecture refactor** of the persona/skill subsystem with dependency injection.
- Runtime governance: policy, budget, audit, workflow, saga, telemetry, memory, and MCP server.
- CI pipeline with `ruff`, `mypy`, `pytest`, `validate-globals`, and `eval/harness.py`.

### Latest additions

- **Comprehensive project review** captured in `.ai/review-findings.md` with P0–P5 issues, SWOT, and development ideas.
- **29 durable workflows** (up from 27), including new `18-data-migration` and `19-incident-response`, with `[TRIGGER]` tags and manifest-based routing.
- **Plugin AST sandbox** in `runtime/plugin.py` blocks denylisted modules and dangerous calls (`eval`, `exec`, `open`, etc.) before `exec_module`.
- **Dashboard hardening** — CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, XSS escaping, SRI for Chart.js, and lazy token generation.
- **MCP client hardening** — per-key `_SEND_LOCKS` and `_send` timeout to prevent process races.
- **SQLite WAL + busy timeout + locks** in `memory/store.py`, `runtime/workflow.py`, and `runtime/saga.py`.
- **Budget `_dirty` flag** in `runtime/budget.py` to avoid unnecessary disk writes.
- **Pydantic-specific validation** in `runtime/kernel.py` instead of broad `except Exception`.
- **Audit redaction** for tokens, keys, secrets, and credentials in `runtime/audit.py`.
- **`.ai/repos-study.md`** — standalone file with an English agent meta-prompt and 30+ curated GitHub repos to evaluate.
- **DevOps / security** — `.github/dependabot.yml`, `CODEOWNERS`, `security.yml` (`pip-audit` + `bandit`), and `bandit`/`pip-audit` in `pyproject.toml` dev dependencies.
- **Conditional rules with YAML frontmatter** (`runtime/rule_frontmatter.py` + `runtime/skill_resolver.py`). Skill and rule files can declare `paths`, `stack`, and `personas` filters. The runtime only loads skills that match the current context, and the MCP `query_rules` endpoint returns active rules only.
- **Fresh-context boundary** (`runtime/kernel.py` + `runtime/budget.py`). A `fresh_context` flag resets per-session budgets and re-derives auto-injected persona/skill keys for clean chat sessions, workflows, and sagas.
- **`ai-os skill` CLI** (`list`, `invoke`, `search`) backed by `SkillResolver`. Searches both the OS root `skills/` and the project `.ai/skills/`.
- **`CV` persona and `cv-writer` skill** for ATS-optimized, bilingual Arabic/English resumes, cover letters, LinkedIn summaries, and portfolio copy.
- **Dashboard design system** (`DESIGN.md`) — dark-first AI command center, cyan/violet/lime tokens, command palette (`Cmd/Ctrl+K`), status pills, bento metric cards, and glass panels.
- **Dashboard and MCP hardening** — configurable CORS origin, CSRF header checks, request-size limits, stronger Bearer token auth, and stricter path/input validation.
- **`mariadb-lord` skill** with Context7 IDs for MariaDB docs, Docker, Node/Python connectors, Laravel + Filament + Nova integration, and multi-tenancy patterns.
- **`page-sections-lord` skill** capturing the section-based landing page builder pattern with a standard spec, Filament Builder blocks, and a setup workflow.
- **Useful-repos research** — 55 verified top GitHub repositories across programming, UI/UX, responsive design, and databases added to `tech-stack/useful-repos.md`.

---

## Quality gates and contributing

Before any handoff, the OS runs:

```bash
ruff check .
mypy
pytest -q
python eval/harness.py
```

All must pass. After changing `rules/`, `tech-stack/`, `workflows/`, or `skills/`, run:

```bash
ai-os memory ingest
graphify update .
```

Star the repository to keep your AI rules automatically updated with the latest engineering standards.

[![Star on GitHub](https://img.shields.io/github/stars/m3taz-ahmed/ai-globals?style=for-the-badge&logo=github&color=FFDD00&labelColor=1a1a2e)](https://github.com/m3taz-ahmed/ai-globals)

- Read the [Contributing Guide](.github/CONTRIBUTING.md) to add your stack.
- Review the [Security Policy](.github/SECURITY.md).
- See the [Code of Conduct](.github/CODE_OF_CONDUCT.md).

> Built for engineers who refuse to settle for mediocre AI output. Engineered with surgical precision by [@m3taz-ahmed](https://github.com/m3taz-ahmed).
