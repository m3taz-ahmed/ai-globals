<div align="center">
  <img src="logo.png" width="160" alt="AI Global OS Logo">
  <h1>AI Global OS</h1>
  <p><strong>Stop letting AI write spaghetti code. Turn it into your Principal Architect.</strong></p>

  <p>
    <img src="https://img.shields.io/badge/Version-4.21.0-6C63FF?style=for-the-badge&logo=buffer&logoColor=white&labelColor=1a1a2e" alt="Version 4.21.0">
    <img src="https://img.shields.io/badge/Status-Self--Healing-00C896?style=for-the-badge&logo=dependabot&logoColor=white&labelColor=1a1a2e" alt="Status: Self-Healing">
    <img src="https://img.shields.io/badge/Architecture-Sovereign-F59E0B?style=for-the-badge&logo=moleculer&logoColor=white&labelColor=1a1a2e" alt="Architecture: Sovereign">
    <img src="https://img.shields.io/badge/License-MIT-3B82F6?style=for-the-badge&logo=opensourceinitiative&logoColor=white&labelColor=1a1a2e" alt="License: MIT">
  </p>
  <p>
    <img src="https://img.shields.io/badge/Tech--Stack-Next.js%2015%20%7C%20Laravel%2013%20%7C%20PostgreSQL%2017-EC4899?style=for-the-badge&logo=nextdotjs&logoColor=white&labelColor=1a1a2e" alt="Stack">
    <img src="https://img.shields.io/badge/Quality%20Gate-SOLID%20%7C%20OWASP%20%7C%20WCAG%202.2-10B981?style=for-the-badge&logo=checkmarx&logoColor=white&labelColor=1a1a2e" alt="Quality Gate">
  </p>

  <p><i>A zero-compromise, version-controlled operating system that eliminates AI context drift, enforces bleeding-edge engineering standards, and governs every line of generated code.</i></p>
</div>

---

## Why AI Global OS exists

Most teams use AI as a high-speed junior developer. It writes fast, but it hallucinates APIs, forgets naming conventions, ignores N+1 queries, and silently ships technical debt.

**AI Global OS** is a Sovereign Architectural Engine. It forces Cursor, Copilot, Claude, Gemini, Windsurf, Cline, Aider, and GitHub Copilot to read from a centralized, version-controlled source of truth *before* writing a single line of code.

| Without the OS | With the OS |
| :--- | :--- |
| Context drift after a few prompts | Rules hard-loaded every session |
| Deprecated packages and silent tech debt | Exact-version tech-stack locked via live MCP docs |
| Raw SQL, missing XSS filters, weak secrets | OWASP, zero-trust, and RBAC enforced by default |
| Random drive-by refactoring | Surgical changes with policy, budget, and audit gates |

[Read this in Arabic](README-AR.md)

---

## Activate in 60 seconds

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
   ai-os check edit
   ai-os run 02-execution
   ai-os memory ingest
   ```

5. **Enable MCP**:
   Add `aios_mcp/config.json` to your IDE MCP config, or run:
   ```bash
   python aios_mcp/aios_server.py
   ```

Your AI is now sovereign. It analyzes every request against SOLID, OWASP, and your exact tech stack before generating code.

---

## What you get

### Nine battle-tested personas

AI Global OS ships with nine hardened professional personas that shape tone, depth, and priorities for every task. Load `global-roles.md` (English) or `global-roles-ar.md` (Arabic) into your agent or IDE to activate them.

- **Principal 10x Engineer & Chief Architect** — infinite scalability, rapid prototyping, zero-defect delivery.
- **Software Tester** — maximum coverage, edge-case hunting, regression prevention.
- **Principal Full-Stack Designer & UX Architect** — flawless journeys, rapid prototypes, pixel-perfect consistency.
- **Master Developer** — system design, secure infrastructure, maximum performance.
- **God-Tier SRE & Cloud Dictator** — multi-region active-active, GitOps automation, chaos engineering.
- **Hardcore Linux Kernel Master & SecOps Warlord** — eBPF tracing, microsecond latency, zero-trust networks.
- **Principal Game Architect & JavaScript Engine Master** — 60 FPS game loops, Capacitor/WebView cross-platform, Babylon.js immersion.
- **Google Play Ecosystem Warlord** — Play policies, IAP/ad monetization, AAB optimization, ANR/crash annihilation.
- **Elite Mobile Game Producer & Full-Stack Innovator** — addictive gameplay, Laravel integrations, Fastlane CI/CD, anti-cheat.

### Runtime governance

- **Policy engine** with `allow/ask/deny` YAML policies and safe AST evaluation.
- **Budget manager** for tokens, cost, and calls per scope.
- **Durable workflow runner** with SQLite state, saga support, and audit logging.
- **Memory service** with SQLite + FTS5, episodic/semantic/factual/procedural layers, graph relations, and optional vector index.
- **MCP server** exposing `query_rules`, `run_workflow`, `check_policy`, `search_memory`, `search_memory_vector`, `get_tech_stack`.
- **CLI `ai-os`** and a web dashboard with CORS, optional bearer auth, and live telemetry.

### Engineering standards

- **Telegraphic Pseudo-Code** for rules, workflows, skills, and tech-stacks — maximum guidance with minimum tokens.
- **Lazy-loaded context layers** — only the relevant standards are loaded per task.
- **Live Ground-Truth** via Context7 MCP before any framework implementation.
- **Zero `any` types**, no inline imports, no dependency downgrades.
- **Mandatory gates**: `ruff`, `mypy`, `pytest`, and `python eval/harness.py` must all pass.

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
├── CHANGELOG.md                  # Release notes
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
├── skills/                       # Compressed AI tools & agent personas
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

## Recent highlights (v4.21.0)

- Runtime kernel with policy, budget, workflow, saga, chat, telemetry, and plugin support.
- Memory ingestion with SQLite + FTS5 + optional vector index.
- MCP server with 12+ tools and dynamic plugin registration.
- CLI `ai-os` with `status`, `check`, `run`, `memory`, `sync`, `policy`, `budget`, `project`, and `doctor`.
- Dashboard with auto-refresh, CORS, optional bearer auth, and 10+ API endpoints.
- Docker hardening with non-root user, healthchecks, and compose support.
- 11 lord-level mastery skills covering database, language, cloud, devops, frontend, backend, messaging, search/vector, AI/ML, Linux, and security.
- 9 hardened personas defined in `global-roles.md` and `global-roles-ar.md`.
- CI pipeline with pinned action SHAs, `ruff`, `mypy`, `pytest`, and `python eval/harness.py`.

---

## Join the movement

Star the repository to keep your AI rules automatically updated with the latest engineering standards.

[![Star on GitHub](https://img.shields.io/github/stars/m3taz-ahmed/ai-globals?style=for-the-badge&logo=github&color=FFDD00&labelColor=1a1a2e)](https://github.com/m3taz-ahmed/ai-globals)

- Read the [Contributing Guide](.github/CONTRIBUTING.md) to add your stack.
- Review the [Security Policy](.github/SECURITY.md).
- See the [Code of Conduct](.github/CODE_OF_CONDUCT.md).

> Built for engineers who refuse to settle for mediocre AI output. Engineered with surgical precision by [@m3taz-ahmed](https://github.com/m3taz-ahmed).
