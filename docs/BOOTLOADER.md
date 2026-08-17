# aiZee — Global Bootloader

The **Global Bootloader** is the entry point that every AI agent (Claude, Cursor, Windsurf, Aider, Devin) reads at session start. It sets the OS root, loads personas, rules, skills, and workflows, and routes all actions through the runtime gate.

## Boot Sequence

```
┌─────────────────────────────────────────────────────────────────┐
│  Session Start                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  1. Read AGENTS.md (this file's source)                   │  │
│  │  2. Set AIZEE_ROOT (env or config.discover_root())     │  │
│  │  3. Read global-roles.md + global-workflow.md + Memory.md │  │
│  │  4. Detect personas: aizee persona detect --multi         │  │
│  │  5. Load returned skills/ before acting                   │  │
│  │  6. If project has spec.md, read it                       │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              ▼                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Runtime Gate (every action)                              │  │
│  │  ┌─────────┐  ┌──────────┐  ┌────────┐  ┌────────────┐  │  │
│  │  │ Probity  │→│ Guardian  │→│ Policy  │→│   Budget   │  │  │
│  │  │ (safety) │  │ (default │  │ (rules) │  │ (tokens/$) │  │  │
│  │  │          │  │  DENY)   │  │         │  │            │  │  │
│  │  └─────────┘  └──────────┘  └────────┘  └────────────┘  │  │
│  │       │              │            │            │          │  │
│  │       ▼              ▼            ▼            ▼          │  │
│  │  ┌──────────────────────────────────────────────────┐    │  │
│  │  │  Decision: ALLOW / DENY / ASK (requires approval)│    │  │
│  │  └──────────────────────────────────────────────────┘    │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              ▼                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Context & Memory                                         │  │
│  │  • Detect tech stack from lockfile → tech-stack/*.md      │  │
│  │  • Query graphify (if graph.json exists) — never raw grep │  │
│  │  • Query Context7 MCP for external libraries              │  │
│  │  • aizee memory ingest when rules/workflows change        │  │
│  │  • Update Memory.md via workflows/17-memory-sync.md       │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              ▼                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Quality Gate (before declaring done)                     │  │
│  │  • ruff check .                                           │  │
│  │  • mypy                                                   │  │
│  │  • aizee test --full  (or pytest -q)                      │  │
│  │  • python eval/harness.py                                 │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## How It Works

### 1. Root Discovery
The bootloader discovers the OS root via (in order):
1. `AIZEE_ROOT` environment variable
2. `config.discover_root()` (walks up from CWD looking for `config.py`)
3. Fallback: current working directory

### 2. Persona Detection
```bash
aizee persona detect --multi "your task description"
```
Returns top-N personas + skills to load. Example:
```json
{
  "persona": "SEC",
  "personas": ["SEC", "ARCH", "DEV"],
  "skills": ["security-auditor", "ai-agents-architect", "backend-api-expert"]
}
```

### 3. Runtime Gate
Every action passes through `runtime/kernel.py`:
```bash
aizee check Read --args '{"tokens": 100}'
```
The kernel evaluates: **probity → guardian → policy → budget** → returns ALLOW/DENY/ASK.

### 4. Agent Configs
The installer symlinks agent configs from the OS root to common locations:
- `.claude/CLAUDE.md`, `.claude/settings.json`, `.claude/skills/`, `.claude/agents/`
- `.devin/skills/global-os/`
- `.windsurf/skills/global-os/`
- `.aider.conf.yml`
- `.cursor/rules/`

### 5. MCP Servers
6 MCP servers are configured (see [MCP servers](../README.md#mcp-servers)):
- `aizee` — core OS tools (policy, memory, workflows, rules)
- `graphify` — codebase knowledge graph
- `context7` — external library docs
- `upwork` / `freelancer` / `fiverr` — freelance platforms
- `linkedin` — content automation

## Non-negotiable Rules
- No `git add .` / `git add -A` / `git commit` / `git push` without explicit user approval
- No destructive git operations (`reset --hard`, `checkout .`, `clean -fd`, `stash`, force push)
- No `eval` in policy code (AST-based safe evaluator only)
- Delete temporary/scratch/test files immediately after use

## Files
| File | Purpose |
|------|---------|
| `AGENTS.md` | Canonical bootloader (read by all agents) |
| `global-roles.md` | Role definitions |
| `global-workflow.md` | Workflow definitions |
| `Memory.md` | Cross-session memory |
| `config.py` | Root discovery + configuration |
| `runtime/kernel.py` | Runtime gate (policy + budget + guardian) |
| `aizee_cli.py` | CLI entry point (`aizee` command) |
