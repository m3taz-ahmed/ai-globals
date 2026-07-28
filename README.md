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
    <img src="https://img.shields.io/badge/Personas-17%20Roles-EC4899?style=for-the-badge&logo=buffer&logoColor=white&labelColor=1a1a2e" alt="17 Personas">
    <img src="https://img.shields.io/badge/Lord%20Skills-11%20Domains-10B981?style=for-the-badge&logo=checkmarx&logoColor=white&labelColor=1a1a2e" alt="11 Lord Skill Domains">
    <img src="https://img.shields.io/badge/Quality%20Gate-SOLID%20%7C%20OWASP%20%7C%20WCAG%202.2-0EA5E9?style=for-the-badge&logo=checkmarx&logoColor=white&labelColor=1a1a2e" alt="Quality Gate">
  </p>

  <p><i>A zero-compromise, version-controlled operating system that eliminates AI context drift, enforces bleeding-edge engineering standards, and governs every line of generated code.</i></p>
</div>

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

[Read this in Arabic](README-AR.md)

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

## For programmers: what it does and why it is different

AI Global OS is not a prompt library. It is a runtime control plane that sits between you and every AI agent you use.

### 1. Persona + Lord Skill composition

The OS ships with **17 personas** (from `ARCH` to `LEGAL`) and **11 lord-level domain skills** (database, AI/ML, cloud, DevOps, security, etc.). For every request the OS detects the most relevant persona *set* and loads the matching skill files. You can also spawn agents with multiple personas, e.g. `ARCH + QA + security-lord`.

```bash
ai-os persona detect --multi "build a secure docker API with postgres"
# Returns a primary persona, secondary personas, primary skills, and lord skills.
```

This is implemented in `runtime/persona.py` + `runtime/skill_resolver.py` and used by `Kernel`, `WorkflowRunner`, and `AgentPool`.

### 2. Runtime governance

Every action passes through a policy + budget gate before it runs.

- **Policy engine** — `allow/ask/deny` YAML rules with safe AST evaluation.
- **Budget manager** — token/cost/call limits per scope.
- **Audit logger** — every decision is recorded.
- **Workflow runner** — durable SQLite-backed execution with saga support.
- **Saga orchestrator** — compensating actions for long-running operations.
- **Telemetry** — structured events for observability.

### 3. Live ground-truth, not stale memory

Before implementing any external library or framework, the OS queries Context7 MCP (`resolve-library-id` then `get-library-docs`) so the generated code matches the actual current API. If `graphify-out/graph.json` exists, the OS navigates the knowledge graph instead of blind `grep`.

### 4. Memory you can trust

The memory service uses SQLite + FTS5 plus optional vector indexing. It stores episodic, semantic, factual, and procedural context. After every rule, tech-stack, or workflow change, `ai-os memory ingest` refreshes the index.

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

### System architecture

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

3. **Install Python dependencies** inside the cloned folder:
   ```bash
   python -m pip install -e .
   ```

4. **Use the CLI**:
   ```bash
   ai-os status
   ai-os persona detect --multi "your task description"
   ai-os check edit
   ai-os run 02-execution
   ai-os memory ingest
   ```

5. **Enable MCP**:
   Add `aios_mcp/config.json` to your IDE MCP config, or run:
   ```bash
   python aios_mcp/aios_server.py
   ```

6. **Point your AI agent at the OS rules**:
   See the next section for the exact file to load into Cursor, Copilot, Claude, Windsurf, Cline, or Aider.

Your AI is now sovereign. It analyzes every request against SOLID, OWASP, WCAG, and your exact tech stack before generating code.

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
13. Git: conventional commits, atomic, never `git add .` or force push, stage only files you modified.
```

For **project-level** rules, use the adapter files in the table above instead.

---

## The 17 personas and 11 lord skill domains

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

Lord skills: `database-lord`, `ai-ml-lord`, `devops-lord`, `cloud-platforms-lord`, `frontend-frameworks-lord`, `backend-frameworks-lord`, `language-lord`, `linux-systems-lord`, `messaging-streaming-lord`, `search-vector-lord`, `security-lord`.

When a prompt touches multiple domains, the OS composes a panel — for example `DEV + API + security-lord` — and loads the union of relevant skill files.

---

## Recent highlights (v4.22.0)

- **Multi-persona + lord skill composition** via `PersonaDetector.detect_multiple`, `SkillResolver`, and `Kernel`/`WorkflowRunner`/`AgentPool` integration.
- **17 personas** defined in `global-roles.md` and `global-roles-ar.md`.
- **9 new persona skill files**: `data-engineer`, `ml-engineer`, `devops-engineer`, `api-architect`, `legal-compliance`, `product-manager`, `technical-writer`, `performance-engineer`, `sre`.
- **CLI enhancements**: `ai-os persona detect --multi` and `ai-os agent spawn --persona ARCH,QA`.
- Clean Architecture refactor of the persona/skill subsystem with injected `PersonaDetector` and `SkillResolver`.
- Runtime governance: policy, budget, audit, workflow, saga, telemetry, memory, and MCP server.
- CI pipeline with `ruff`, `mypy`, `pytest`, `validate-globals`, and `eval/harness.py`.

---

## Join the movement

Star the repository to keep your AI rules automatically updated with the latest engineering standards.

[![Star on GitHub](https://img.shields.io/github/stars/m3taz-ahmed/ai-globals?style=for-the-badge&logo=github&color=FFDD00&labelColor=1a1a2e)](https://github.com/m3taz-ahmed/ai-globals)

- Read the [Contributing Guide](.github/CONTRIBUTING.md) to add your stack.
- Review the [Security Policy](.github/SECURITY.md).
- See the [Code of Conduct](.github/CODE_OF_CONDUCT.md).

> Built for engineers who refuse to settle for mediocre AI output. Engineered with surgical precision by [@m3taz-ahmed](https://github.com/m3taz-ahmed).
