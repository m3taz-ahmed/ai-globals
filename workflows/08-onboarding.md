# Workflow 08: Project Onboarding & AI Architect Initialization

> [!IMPORTANT]
> **Trigger:** Starting work on a new project, switching to a different project, or re-initializing after a session break.
> **Goal:** Get from "blank agent" to "Sovereign Architect" as fast as possible — and deliver the first high-quality response within 60 seconds of activation.

---

## ⚡ 60-Second Activation (The Fast Path)

Send this single directive to your AI agent. It does everything:

```
Start immediately by reading your operating protocols from the .ai directory root.
Do not rely on any prior assumptions.
Operate as the Principal 10x Engineer & Chief Architect.
```

**What the agent MUST do upon receiving this:**
1. Read `rules/core-behavioral-compact.md` and `global-roles.md` (Layer 0)
2. Read `rules/anti-patterns.md` (Layer 1)
3. Scan `composer.json` / `package.json` for the tech stack
4. Load matching tech-stack files from `./tech-stack/`
5. Report the "Handoff Summary" below

**Your "Aha! Moment":** The very next response will cite specific rules by name (`rules/anti-patterns.md §3`), reference exact versions (`Laravel 12.x`), and deliver architecturally-sound code — not generic output.

---

## Context Loading Sequence

```
Layer 0 (ALWAYS — load first, every task)
  ├── rules/core-behavioral-compact.md  ← 4 behavioral principles, < 50 lines
  └── global-roles.md                   ← Quality gates & communication protocol

Layer 1 (ALWAYS — load immediately after Layer 0)
  └── rules/anti-patterns.md            ← Hard-stop constraints

Layer 2 (ON-DEMAND — load only when relevant to current task)
  ├── Onboarding/behavioral  → rules/llm-behavioral-guidelines.md
  ├── Security task          → rules/security-standards.md
  ├── External APIs          → rules/api-integration-standards.md
  ├── Logging/monitoring     → rules/observability-standards.md
  ├── Performance work       → rules/performance-standards.md
  ├── Git/PR work            → rules/git-standards.md
  ├── SaaS features          → rules/saas-standards.md
  └── Architecture review    → rules/principal-architect.md

Layer 3 (ON-DEMAND — task workflow + detected tech-stack)
  ├── Workflow: [match task type → workflows/NN-name.md]
  └── Tech-stack: [match detected versions → tech-stack/xxx.md]
```

---

## Repository Setup (First Time Only)

When onboarding to a **new project** (not a re-initialization):

- [ ] **Memory:** Create `MEMORY.md` in the project root if it doesn't exist
- [ ] **Git:** Verify `.gitignore` and `.editorconfig` align with `rules/git-standards.md`
- [ ] **Tech-Stack Scan:** Run auto-discovery per `global-roles.md §3`
- [ ] **Auto-Discovery:** If a detected tech version has no rule file, generate and propose one

---

## Baseline Audit (New Projects Only)

A "Mini Deep-Scan" to establish the project's current state:

1. **Architecture Check** — Thin controllers? Service layer present? Proper model scoping?
2. **Security Quick-Scan** — `$guarded = []`? Raw SQL? Missing auth middleware? Debug mode on?
3. **Dependency Health** — Run `composer audit` and `npm audit` for known CVEs
4. **Test Coverage** — What % coverage exists? Which critical paths are untested?
5. **Tech Debt** — Log all red flags in the project's `MEMORY.md`

---

## Handoff Summary (Required Output)

After every onboarding (re-initialization or first-time), the agent MUST report:

```
## Onboarding Complete — Sovereign Mode Active

**Stack Detected:**
- Laravel 12.x / PHP 8.4 / Filament 4.x
- React 19 / TypeScript 5.x / Vite 7
- MySQL 8.4 / Pest 4

**Rules Loaded:**
- [x] Layer 0: core-behavioral-compact.md, global-roles.md
- [x] Layer 1: anti-patterns.md
- [x] Layer 2: [list loaded on-demand rules]
- [x] Layer 3: laravel-12.md, php-8-4.md, react-ecosystem.md

**Red Flags Found:** [N critical / N major / N minor]
- 🔴 [Critical issue if found]
- 🟡 [Major issue if found]

**Recommended First Action:**
[The single most important thing to address first]

Ready to operate as Principal Architect. What's the first task?
```
