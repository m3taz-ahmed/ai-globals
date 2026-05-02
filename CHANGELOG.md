# Changelog

All notable changes to the AI Globals system are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/) and [Conventional Commits](https://www.conventionalcommits.org/).

## [3.1.0] — 2026-05-02
### Added
- **Design Foundations:** `design-foundations.md` (Bento Grids, Glassmorphism, Neumorphism, Modern Gradients).
- **Responsive UI:** `responsive-ui.md` (Container Queries, Adaptive Layouts, Mobile UX).
- **Accessibility Standards:** `accessibility-standards.md` (WCAG 2.1 AA Compliance).
- **Bilingual Mastery:** `bilingual-mastery.md` (RTL/LTR, Logical Properties, Arabic Typography).

### Changed
- **Global Roles:** `global-roles.md` (Added Font Selection Gate, UI Stack Discovery, and Aesthetics Mandate).
- **Frontend Modern:** `frontend-modern.md` (Added Framer Motion and GSAP animation standards).

## [3.0.1] — 2026-05-02
### Added
- **New Workflow:** `00-prompt-architecting.md` for refining user prompts before execution.
- **Triggers:** Simplified to a single trigger `/prompt` for the global workflow routing.
- **Role Expansion:** Defined "Prompt Architecting Mode" in `global-roles.md`.


## [3.0.0] — 2026-05-02
### Added
- **New Tech-Stacks:** `pest-4.md`, `spatie-permission.md`, `spatie-activitylog.md`, `filament-shield.md`, `vite-7.md`, `alpine-3.md`, `postcss-8.md`.
- **New Workflows:** `06-maintenance.md` (System Maintenance), `07-security-audit.md` (Security Audit), `08-onboarding.md` (Project Onboarding).
- **Automation:** `scripts/validate-globals.ps1` for repository hygiene.

### Changed
- **Core Protocols:** `global-roles.md` (added Proactive Auditing), `global-workflow.md` (added Maintenance routing).
- **Rule Hardening:** `security-standards.md`, `performance-standards.md`, `code-quality.md` updated to elite 2025 standards.
- **Tech-Stack Refinement:** Expanded `php-8-4.md`, `mysql-8-4.md`, `filament-4.md`, `laravel-12.md`.
- **Hygiene:** Normalized all file line endings to LF.

## [2.1.0] — 2026-05-01

### Added
- `rules/anti-patterns.md` — Comprehensive negative constraints & forbidden patterns (7 categories: code structure, error handling, security, performance, database, testing, AI workflow)
- `rules/api-integration-standards.md` — External API integration standards (HTTP client, error handling, retry/resilience, authentication, webhook handling, response caching, versioning)
- `rules/observability-standards.md` — Observability & monitoring standards (structured logging, health endpoints, error tracking, alerting strategy, development observability, audit trails)

### Changed
- `global-roles.md` — Added §8 External Integration & Observability Mandate. Added Anti-Pattern Compliance to §4 Quality Gates.
- `global-workflow.md` — Added Anti-Pattern Cross-Check and External Integration Check to Step 2 (THINK). Updated Base Context list in Step 1 with new rule files.
- `README.md` — Updated repository tree with 3 new rule files.

## [2.0.0] — 2026-05-01

### Added
- `.gitignore` — OS/editor artifact prevention
- `.editorconfig` — LF line endings, UTF-8, consistent indentation enforcement
- `rules/code-quality.md` — Clean Code standards, naming conventions, SOLID enforcement
- `rules/performance-standards.md` — Query budgets, caching strategy, queue patterns, Web Vitals
- `tech-stack/livewire-3.md` — Livewire component architecture (Filament dependency)
- `tech-stack/vite-6.md` — Vite build tool standards (Laravel asset bundler)
- `workflows/04-deployment.md` — Deployment & release workflow with rollback procedures
- `workflows/05-code-review.md` — Code review protocol with security/performance checklists
- `monthly-maintenance-prompt.md` — Comprehensive monthly audit protocol with checklists
- `MEMORY.md` — Audit log and architectural decision records
- `CHANGELOG.md` — This file

### Changed
- `global-roles.md` — Added §4-§7 (Quality Gates, Communication, Error Handling, Cross-Project Consistency)
- `global-workflow.md` — Added Steps 5-7 (Verification, Documentation Sync, Handoff), generalized scratchpad, directory-pattern references
- `rules/principal-architect.md` — Added §6 Error Handling Philosophy, §7 Testing Standards
- `rules/security-standards.md` — Added §5 Rate Limiting, §6 CORS, §7 Dependency Security
- `rules/git-standards.md` — Added §3 Branching, §4 PR Requirements, §5 Protected Branches
- `rules/environment-windows.md` — Added §3 PowerShell, §4 WSL Integration
- `workflows/01-planning.md` — Added Risk Assessment Matrix, Dependency Analysis
- `workflows/02-execution.md` — Added Test-Alongside Workflow, Code Review Self-Check
- `workflows/03-debugging.md` — Added Structured Debugging Protocol, Post-Mortem Template
- `README.md` — Added ToC, repo tree, Quick Reference, Contributing Guidelines
- `update-me.md` — Restructured with metadata and usage guidance
- `tech-stack/laravel-boost.md` — Removed duplicated content from laravel-12.md

### Improved
- Expanded 8 thin tech-stack files to comprehensive coverage: `mysql-8-3`, `nodejs-22/23/24`, `tailwind-3`, `tailwind-4-1`, `php-8-3`
- Added `[SPECULATIVE]` headers to 4 unreleased-version files: `php-8-5`, `filament-5`, `laravel-13`, `mysql-9-7`
- Normalized all 31 `.md` files from CRLF → LF line endings

### Removed
- `monthely-maintenance-prompt.md` — Replaced by `monthly-maintenance-prompt.md` (typo fix + expansion)

## [1.0.0] — 2026-05-01

### Added
- Initial repository structure with rules, tech-stack, and workflows
- Core files: global-roles.md, global-workflow.md, update-me.md
- README.md with system documentation
