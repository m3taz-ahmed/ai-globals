# AI Globals — Audit & Decision Log

> This file tracks system-level audits, architectural decisions, and auto-discovered tech-stack additions.
> Historical entries have been archived to [MEMORY-archive.md](file:///D:/server/.ai/MEMORY-archive.md).

## 2026-06-09 — AI OS Memory Engine (v4.16.0)

**Scope:** Integrated `turbovec` as the native local vector search engine for the Global AI OS.
**Trigger:** Manual — User request to analyze and adopt `turbovec` repo.
**Agent:** Antigravity (Gemini 3.1 Pro)

### Actions Taken
- **Standardization:** Created `tech-stack/turbovec-standards.md` establishing `turbovec` as the sovereign vector index and prohibiting external vector DBs.
- **Module Creation:** Built `scripts/ai_memory_engine.py` to wrap the `IdMapIndex` functionality for adding/searching memory vectors.

### Architectural Decisions
1. **Efficiency Over Complexity:** Utilizing a 4-bit scalar quantized index directly in memory avoids the overhead of managing Dockerized databases (like Milvus or Qdrant), fitting our local-first philosophy.
2. **Hybrid Search Foundations:** Using `IdMapIndex` allows integration with external permissions/ACLs using `turbovec`'s SIMD allowlist filtering.

---

## 2026-06-06 — Third-Party AI Capabilities Standard (v4.16.1)

**Scope:** Defined the official package manager and standard for extending AI capabilities without bloating the native OS.
**Trigger:** Manual — User request and architectural discussion
**Agent:** Antigravity (Gemini 3.1 Pro)

### Architectural Decisions
1. **`vercel-labs/skills` as Standard:** Adopted `vercel-labs/skills` as the official standard for integrating third-party APIs (AWS, Stripe) and domain-specific AI workflows.
2. **Strict Separation of Concerns:** Native OS rules (`d:\server\.ai\workflows`) will NOT be converted to `SKILL.md` format. Vercel Skills (`npx skills`) will be used strictly as ephemeral, external plugins to preserve the OS's git-based centralization and portability.

---

## 2026-06-06 — Native Persistent Memory System (v4.16.0)

**Scope:** Implemented a native context-preservation system inside the Global AI OS (inspired by claude-mem) to maintain project-specific context across sessions without third-party tools.
**Trigger:** Manual — User request and architectural discussion
**Agent:** Antigravity (Gemini 3.1 Pro)

### Actions Taken
- **Workflow Creation:** Created `workflows/09-memory-sync.md` to extract, compress, and save session learnings into a local `./.ai/active-context.md` file.
- **Workflow Automation:** Updated `global-workflow.md` (Layer 1 and Step 6) to read from and write to the local active context automatically at the end of major tasks.

### Architectural Decisions
1. **Native Implementation over Third-Party Tools** — Building this natively inside the AI OS ensures full control, avoids conflicts with existing CLI tools, and integrates perfectly with the existing Markdown/Workflow ecosystem.
2. **Relative Pathing (`./.ai/active-context.md`)** — Scoping the memory per-project avoids bloat and cross-contamination of project contexts, solving the multi-tenant memory problem gracefully.
3. **Auto-Triggering Memory Sync** — Mandated that the AI natively invokes the memory sync sequence without requiring manual user prompts to simulate a true "persistent memory" experience.

---

## 2026-05-29 — MCP Initialization & Windows Quoting Fix (v4.15.1)

**Scope:** Repairing Windows-specific shell quoting and variable expansion bug causing StitchMCP and all cascading MCP servers to fail during IDE startup.
**Trigger:** Manual — MCP Error resolution
**Agent:** Antigravity (Gemini 3.5 Flash)

### Actions Taken
- **MCP Configuration Hardening:** Refactored `C:\Users\Moataz\.gemini\antigravity-ide\mcp_config.json` to spawn `StitchMCP` directly using `npx.cmd` instead of calling `cmd.exe /c` with backslash-escaped quotes.
- **Environment Variable Binding:** Switched from Windows shell-level environment variable expansion (`%STITCH_API_KEY%`) to `mcp-remote` native token substitution (`${STITCH_API_KEY}`).

### Architectural Decisions
1. **Direct Binary Spawning over Shell Wrapper** — Spawning batch/executable targets (`npx.cmd`) directly instead of launching an intermediate shell (`cmd.exe /c`) avoids multi-layered quote escaping and argument tokenization bugs on Windows.
2. **Native Tool Substitution** — Utilizing `mcp-remote`'s internal environment variable replacement parser ensures secure token injection without relying on OS-level command-line expansions.

---

## 2026-05-27 — Superpowers Methodology & Prompt Architecting Upgrade (v4.14.0)

**Scope:** Full System Deep-Scan and Upgrade to natively integrate `obra/superpowers` behavioral methodologies and harden prompt architecting capabilities.
**Trigger:** Manual — User Objective implementation
**Agent:** Antigravity (Gemini 3.1 Pro)

### Actions Taken
- **Workflow Hardening:** Updated `global-workflow.md` to explicitly mandate reading `useful-repos.md` in Layer 1, and injected `obra/superpowers` philosophies (Spec Teasing, Digestible Chunking, Red/Green TDD) into `workflows/01-planning.md`.
- **Prompt Architecting Upgrade:** Refined `workflows/00-prompt-architecting.md` to act as a strict quality gate that extracts specifications before any implementation begins.
- **Skill Alignment:** Ensured `workflows/02-execution.md` and `rules/anti-patterns.md` mandate the execution of local skills (`tdd-workflows`, `subagent-driven-development`) for complex changes.
- **Tool Discovery:** Added `VoltAgent/awesome-design-md` to `useful-repos.md` to standardise UI contexts.

### Architectural Decisions
1. **Spec Teasing as a Quality Gate** — By enforcing a strict halt-and-ask mechanism, we prevent AI from fabricating implementation details for ambiguous requirements.
2. **Digestible Chunking** — Presenting plans in small, readable chunks ensures higher fidelity user sign-off.
3. **Mandatory Skills Delegation** — Relying on specialized local skills for execution ensures autonomous agents adhere to Red/Green TDD patterns rather than improvising monolithic changes.

---

## 2026-05-14 — Sovereign Audit & Ecosystem Convergence (v4.11.0)

**Scope:** High-fidelity architectural audit across Analyst, System Design, Refactor, and Critic personas.
**Trigger:** User request `/analyst /systemdesign /refactor /critic`
**Agent:** Antigravity (Gemini 3.1 Pro)

### Actions Taken
- **Saga Reconciliation Directives:** Injected explicit state machine verification handshakes in `security-standards.md` and `global-workflow.md` to guarantee sovereign multi-agent state consistency during parallel subagent task delegation.
- **Cache-Retry Interlock Hardening:** Documented deterministic tracking headers (`X-Cache-Lookup`, `X-Cache-Interlock`) under advanced caching patterns to prevent cascading database retries on stale/expiring cache entries.
- **General File Reference Scans:** Expanded `validate-globals.ps1` to parse, whitelist, and resolve non-section file link references, uncovering and resolving latent broken file links across the repository.
- **Bilingual Convergence:** Synchronized versions across English and Arabic document trees to **v4.11.0** and updated the integrity manifest dynamically.

---

## 2026-05-12 — Artifacts Management Decision

**Scope:** Standardizing the exclusion of local AI session artifacts.
**Trigger:** User request during AI-Globals architectural planning.
**Agent:** Antigravity (Gemini 3.1 Pro)

### Actions Taken
- Added `brain/` directory to `.gitignore` to prevent tracking of local Antigravity session artifacts.
- Established a mandatory rule to ALWAYS add any newly generated workspace artifact folders to `.gitignore` automatically in future sessions.

---

## 2026-05-09 — Self-Healing Sovereignty (v4.5.0)

**Scope:** Resolution of cross-domain logical friction and implementation of automated healing.
**Trigger:** Manual — /critic + Deep Structural Integrity
**Agent:** Antigravity (Gemini 3 Flash)

### Findings Summary
| Category | Issue | Resolution |
|---|---|---|
| Logic | Resilience/Cache Conflict | Implemented Cache-Retry Interlock. |
| Logic | Aesthetic/Perf Conflict | Implemented Critical Path Protection mandate. |
| Integrity | Manual Maintenance | Implemented `-Fix` mode in `validate-globals.ps1`. |

### Actions Taken
- Upgraded `validate-globals.ps1` to v4.5.0.
- Injected 3 Contextual Interlocks across rule files.
- Synchronized all version strings.

---

## 2026-05-09 — Full System Deep-Scan & Hardening (v4.4.0)

**Scope:** Critical audit of tech-stack rules to resolve performance fallacies and domain gaps.
**Trigger:** Manual — /critic (Devil's Advocate review)
**Agent:** Antigravity (Gemini 3 Flash)

### Findings Summary
| Category | Issue | Resolution |
|---|---|---|
| Performance | `json_validate` double-parsing fallacy | Gated usage to pass-through only |
| Bilingual UX | Missing `mb_str_pad` standard | Added as mandatory for UI alignment |
| Resilience | Weak `#[\Override]` enforcement | Mandated static analysis check in CI |
| Architecture | Missing Anon Readonly classes | Integrated into PHP 8.3 spec |

### Actions Taken
- Hardened `tech-stack/php-8-3.md` with high-fidelity standards.
- Synchronized `CHANGELOG.md` to v4.4.0.
- Updated system integrity manifest.
