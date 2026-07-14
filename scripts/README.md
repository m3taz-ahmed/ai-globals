# `scripts/` — Automation & Validation Tools

Self-healing and utility engine for AI Global OS v4.20.0.

---

## Validators

### `validate-globals.py` — Source-of-Truth Integrity Validator (v4.20.0)

Python validator. Single source of logic. All checks run here.

```bash
# Standard scan
python scripts/validate-globals.py

# Full scan — bypass SHA-256 cache
python scripts/validate-globals.py --force

# Self-healing auto-correct (CRLF, BOM, trailing newlines, broken refs)
python scripts/validate-globals.py --fix

# Dry-run preview of fixes
python scripts/validate-globals.py --fix --dry-run

# Force-regenerate integrity.manifest
python scripts/validate-globals.py --generate-manifest
```

**Checks performed:**

| Check | Description |
|---|---|
| **Title** | AI files: `[FILE]/[TECH]/[WORKFLOW]/[SKILL]` or YAML `name:`. Human docs: `# H1` / `<h1>`. |
| **Struct** | AI files MUST contain `[OBJ]` and `[RULES]`. |
| **Encoding** | Detects mojibake artifacts (`â€"`, `U+FFFD`) |
| **Line Endings** | All files must use LF (flags CRLF) |
| **BOM** | BOM-less UTF-8 only |
| **Trailing Newline** | Single trailing newline required |
| **Cross-References** | Validates `file.md §N` section links |
| **File References** | Validates `.md` file refs exist in the repo |
| **Symbolic Codes** | All `[XXX-NN]` codes must be defined in `rules/vocabulary.md` |
| **Secrets** | Entropy-based detection of leaked credentials |
| **Version** | README / CHANGELOG / scripts all at the same version |
| **Integrity Manifest** | SHA-256 hashes detect unauthorized changes |

**Scope:** `*.md` at root + `rules/` + `tech-stack/` + `workflows/` + `skills/` (recursive). Honors `.aiignore`.

**Exit codes:** `0` = clean · `1` = errors · `2` = misconfig (e.g. missing `rules/vocabulary.md`)

---

### `validate-globals.ps1` — PowerShell Thin Wrapper (v4.20.0)

Delegates all logic to `validate-globals.py`. Accepts identical flags.

```powershell
.\scripts\validate-globals.ps1
.\scripts\validate-globals.ps1 -Force
.\scripts\validate-globals.ps1 -Fix
.\scripts\validate-globals.ps1 -Fix -DryRun
.\scripts\validate-globals.ps1 -GenerateManifest
```

**Requirements:** PowerShell 7+, Python 3.10+.

---

## Free AI Keys

### `fetch-free-keys.py` — Free API Key Discovery

Fetches and lists available free-tier API keys from community sources for AI model providers.

```bash
python scripts/fetch-free-keys.py
```

---

## OpenCode Integration

### `run-opencode-free.ps1` / `run-opencode-free.cmd`

Launches OpenCode with free-tier model configuration. Cross-platform: `.ps1` for PowerShell, `.cmd` for CMD/batch.

```powershell
.\scripts\run-opencode-free.ps1
```

---

## Graphify MCP

### `graphify_mcp_wrapper.py` — Graphify MCP Server Wrapper

Wraps the `graphify` CLI as an MCP (Model Context Protocol) server, enabling AI agents to query the codebase knowledge graph via tool calls.

```bash
python scripts/graphify_mcp_wrapper.py
```

---

## Community Skill Ingestion

### `ingest-community-skill.ps1` — Skill Package Importer

Clones a community skill repository into `skills/`, validates format, and registers it. Enforces Telegraphic Pseudo-Code compression per `global-roles.md §7`.

```powershell
.\scripts\ingest-community-skill.ps1 -RepoUrl <url> -SkillName <name>
```

---

## UI/UX Pro Max

### `ui-ux-pro-max/` — Design Intelligence Engine

Multi-file subsystem for generating UI/UX specifications. Contains:

| File | Purpose |
|---|---|
| `scripts/core.py` | Core generation engine |
| `scripts/design_system.py` | Design system rule extraction |
| `scripts/search.py` | Asset and pattern search |
| `data/_sync_all.py` | Syncs all CSV data sources |
| `data/*.csv` | Design tokens, typography, colors, icons, UX guidelines |
| `data/stacks/*.csv` | Stack-specific UI patterns (React, Next.js, Vue, etc.) |

```bash
python scripts/ui-ux-pro-max/scripts/core.py
```

---

## CI

See `.github/workflows/validate.yml` — runs `validate-globals.py --force` on every push/PR.
