# Changelog

> All notable changes are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/) and [Conventional Commits](https://www.conventionalcommits.org/).

## [v4.7.1] - 2026-05-11 - Tech-Stack Quality Audit & Best-Practice Alignment

### Fixed
- **rules/:** Corrected H1 titles in `caching-standards.md`, `ci-cd-standards.md`, `database-scaling.md`, `devops-standards.md`, and `testing-standards.md` from `Tech-Stack:` to proper domain-specific titles matching the rules directory convention.
- **tech-stack/README.md:** Updated coverage table from 37 files to 60 files, added all 22 new tech-stack files to the category table, updated lazy-loading note.
- **rules/README.md:** Added 5 new rule files (`caching-standards.md`, `ci-cd-standards.md`, `database-scaling.md`, `devops-standards.md`, `testing-standards.md`) to the file reference table.
- **README.md:** Fixed version alt text (4.6.0 → 4.7.0) and added version tag to Sovereignty line for validation script compatibility.

### Changed
- **tech-stack/nextjs-15.md:** Expanded from 34 to 70 lines. Added Partial Prerendering (PPR), `after()` API, Turbopack dev server, `next.config.ts` enforcement, React 19 `use()` hook, `dynamicIO` config, and new compliance checks.
- **rules/testing-standards.md:** Expanded from 33 to 82 lines. Added Vitest/React Testing Library patterns, Playwright Page Object Model, visual regression guidance, coverage enforcement tooling, snapshot management, frontend testing standards, and 4 new compliance checks.
- **tech-stack/shadcn-ui.md:** Fixed deprecated CLI command (`shadcn-ui` → `shadcn`), added Shadcn CLI v2 init/diff/registry patterns, added new hard constraint for deprecated command, added compliance check.
- **tech-stack/clerk-auth.md:** Expanded from 31 to 62 lines. Added Organizations and multi-tenancy (webhooks, membership roles, `<OrganizationSwitcher>`), session token management, `publicMetadata` vs `privateMetadata` safety, `auth()` vs `currentUser()` guidance, and 2 new compliance checks.
- **tech-stack/zod-validation.md:** Updated for Zod v4. Added Zod Mini (`zod/v4/mini`), `z.interface()`, `z.file()`/`z.blob()`, improved `flatten()`/`format()` API, `errorMap`, Server Action typing, v3 migration constraint, and bundle size compliance check.
- **tech-stack/typescript-5.md:** Added `using` keyword (Explicit Resource Management), `--isolatedDeclarations`, `--module NodeNext`, native TC39 decorators vs legacy `experimentalDecorators`, `Symbol.metadata`, and 2 new compliance checks.
- **tech-stack/tanstack-query.md:** Replaced query key factory with `queryOptions()` pattern (v5 best practice). Added `useSuspenseQuery()` for Suspense integration, `useMutationState()`, and SSR/Suspense-specific hard constraints and compliance checks.
- **tech-stack/framer-motion.md:** Added `motion` component (v11+ replacing `m`), React 19 support, `LazyMotion` with `domAnimation` for bundle optimization, Next.js SSR isolation rules (Client Component boundary), and SSR safety compliance check.

### Added
- Cross-references added between related rule and tech-stack files: `caching-standards.md` ↔ `redis-7.md`/`laravel-octane.md`, `database-scaling.md` ↔ `postgresql-17.md`, `devops-standards.md` ↔ `docker-containers.md`/`terraform-iac.md`, `ci-cd-standards.md` ↔ `github-actions-ci.md`, and reverse references.

---

## [v4.7.0] - 2026-05-10 - Bleeding-Edge Audit & Supply Chain Hardening

### Changed
- **tech-stack/laravel-octane.md:** Added Driver Selection Matrix (FrankenPHP vs RoadRunner vs Swoole), `--max-requests` lifecycle management, memory leak detection strategy, HTTP/3 protocol support, graceful deployment/reload patterns, and persistent connection guidance.
- **rules/devops-standards.md:** Added Progressive Delivery (canary deployments, feature flags), Chaos Engineering as continuous practice, GitOps with drift detection, self-healing infrastructure, OIDC keyless authentication, Platform Engineering golden paths, and Policy-as-Code (OPA/Kyverno).
- **rules/caching-standards.md:** Added Cache-Aside/Write-Through/Write-Behind pattern matrix, Redis Cluster/Sentinel HA guidance, graceful cache degradation with circuit breakers, serialization standards (MessagePack/igbinary), payload compression (LZ4/zstd), and TTL policy framework.
- **rules/database-scaling.md:** Added PostgreSQL 17-specific features: `JSON_TABLE`, `sslnegotiation=direct`, redesigned vacuum (20x lighter), `pg_wait_events`, incremental backups. Added JSONB/GIN indexing strategy, aggressive autovacuum tuning, advisory locks, Aurora I/O-Optimized, and Aurora Global Database multi-region DR.
- **rules/ci-cd-standards.md:** Added OIDC Keyless Authentication, SLSA Level 3 provenance (slsa-github-generator + Sigstore/Cosign), SHA-pinned GitHub Actions, SBOM generation (syft/trivy), ephemeral runners, least-privilege GITHUB_TOKEN permissions, environment-scoped secrets, deployment risk tags, and DORA metrics tracking.

### Research Basis
- 10 targeted web searches covering Laravel 13 (released March 2026), PostgreSQL 17, AWS EKS/Aurora 2026 best practices, CI/CD supply chain security (SLSA/OIDC), and modern DevOps (progressive delivery, chaos engineering, GitOps).

---

## [v4.6.0] - 2026-05-10 - High-Scale SaaS Blueprint

### Added
- **Tech-Stack:** 22 new comprehensive rule files covering Next.js 15, TypeScript 5, PostgreSQL 17, Redis 7, Laravel Octane/Horizon/Reverb, Clerk Auth, Shadcn/ui, Zustand, TanStack Query, Zod, Docker, AWS Infrastructure, Cloudflare Edge, Terraform, GitHub Actions, Sentry, Meilisearch, ClickHouse, Stripe, and Framer Motion.
- **Rules:** 5 new architectural standards covering Testing, DevOps, Caching, Database Scaling, and CI/CD Governance.

### Changed
- **README.md:** Updated version to v4.6.0, updated the Tech-Stack badges to reflect the new stack (Next.js 15 / Laravel 12 / PostgreSQL 17), and highlighted the new SaaS blueprint milestone.

---

## [v4.5.1] - 2026-05-09 - Marketing & Professionalism Audit

### Added
- **README.md:** Complete overhaul — premium shield badges with `labelColor`, "Why This Matters" section, 3-step surgical Quick Start, collapsible milestone history, and contribution links.
- **CONTRIBUTING.md:** Professional contributor onboarding — prerequisites, workflow, Conventional Commits convention, PR checklist, and "First Contribution" guide.
- **SECURITY.md:** Vulnerability disclosure policy with supported versions table, private disclosure process, and response timeline SLAs.
- **CODE_OF_CONDUCT.md:** Contributor Covenant 2.1 adapted for a technical engineering community.
- **`.github/ISSUE_TEMPLATE/bug_report.md`:** Structured bug report template with severity triage.
- **`.github/ISSUE_TEMPLATE/feature_request.md`:** Feature request template requiring ❌/✅ examples.
- **`.github/ISSUE_TEMPLATE/tech_stack_request.md`:** Dedicated template for tech-stack rule file requests.
- **`.github/PULL_REQUEST_TEMPLATE.md`:** PR checklist enforcing validation, changelog, and quality gates.
- **`rules/README.md`:** Explains the layered constraint loading system with file reference table.
- **`tech-stack/README.md`:** Explains the lazy-loading RAG pattern, naming conventions, and full coverage table.
- **`workflows/README.md`:** Explains the routing map, trigger conditions, and execution model.
- **`scripts/README.md`:** Documents `validate-globals.ps1` with all flags, exit codes, and CI integration example.

### Changed
- **`workflows/08-onboarding.md`:** Redesigned for fastest possible "Aha! moment" — 60-Second Activation box, visual context-loading checklist, and mandatory structured Handoff Summary output.
- **`EXAMPLES.md`:** Added Quick Reference summary table at top. Added 3 new high-value sections: §5 Laravel 12 mass-assignment & N+1, §6 React XSS & data exposure, §7 SQL injection prevention. Updated Anti-Patterns Summary table to cover all 9 patterns with severity ratings.
- **`CHANGELOG.md`:** Moved preamble to line 1 (was incorrectly positioned at line 92).

---

## [v4.5.0] - 2026-05-09 - Self-Healing Sovereignty

### Added
- **Self-Healing Mode:** `validate-globals.ps1` v4.5.0 now includes a `-Fix` flag to auto-correct encoding artifacts, line endings, and broken cross-references using fuzzy resolution logic.
- **Contextual Interlocks:** Added cross-domain logical rules to resolve friction between Performance, Resilience, and Aesthetics (e.g. Cache-Retry Interlock).
- **Idle-Callback Mandate:** High-fidelity UI assets must now use non-blocking initialization to protect the critical rendering path.

### Changed
- **Performance Standards:** Integrated Logic-Logging interlocks for optimized parsing vs debugging context.

## [v4.4.0] - 2026-05-09 - Deep Structural Integrity

### Added
- **Cross-Reference Verification:** `validate-globals.ps1` v4.4.0 now performs deep structural analysis, verifying every `ref: ... §N` section link across the entire repository.
- **Secret Guard:** Implemented automated entropy and pattern-based secret scanning in the validation engine to prevent accidental credential commits.
- **Rule Propagation logic:** The validation script now detects changes in core rules and forces a full system scan, preventing manifest-based bypasses of new standards.

### Changed
- **php-8-3.md:** Integrated anonymous `readonly` class support and hardened type system standards.
- **validate-globals.ps1:** Complete refactor of version detection and integrity manifest logic.

## [v4.3.1] - 2026-05-09 - Architectural Hardening (Audit v1)

### Changed
- **php-8-3.md:** Hardened standards following `/critic` audit. 
    - Resolved `json_validate()` performance fallacy (double-parsing).
    - Added mandatory `mb_str_pad()` for bilingual UI integrity.
    - Mandated static analysis enforcement for `#[\Override]`.
    - Simplified Randomizer engine requirements.
    - Added guidance for anonymous `readonly` classes.

## [v4.3.0] - 2026-05-09 - Architectural Resilience

### Added
- **Incremental Validation:** `validate-globals.ps1` v4.3.0 now uses SHA-256 manifests to skip unchanged files, significantly improving validation speed for small edits.
- **Audit-Driven Upgrades:** `rules/security-standards.md §8` — Formalized protocol for dependency upgrades, mandating impact analysis for major version jumps instead of hard pinning.
- **Hardened Execution Loop:** `global-workflow.md Step 4` — Integrated high-fidelity verification patterns (Refactor, UI, API) and a mandatory "Surgical Test" check directly into the core protocol.

### Changed
- **validate-globals.ps1:** Added `-Force` switch to bypass incremental skipping and run a full scan.
- **README:** Updated version to v4.3.0 and highlighted Resilience milestones.

## [v4.2.0] - 2026-05-09 - Refactor / Security / Optimize Deep-Scan

### Refactored
- **Behavioral Deduplication:** `llm-behavioral-guidelines.md` now references `core-behavioral-compact.md` for base principles, providing only expanded self-tests and guidance (~70% duplication eliminated).
- **global-roles.md §9:** Replaced inline self-test checklist with reference to behavioral rule files.
- **global-roles.md §8:** Trimmed to reference domain rules instead of restating their content.
- **principal-architect.md §6/§7:** Added cross-references to `rules/anti-patterns.md` to reduce overlap.
- **validate-globals.ps1:** Replaced double-pass file reading with single-pass content caching.
- **CHANGELOG:** Normalized all version headers to use `v` prefix consistently.
- **README:** Updated version from v4.0.0 to v4.2.0. Updated Layer descriptions to reflect new Layer 1/2 structure.

### Fixed
- **Mojibake:** Replaced `â€—` with proper em-dash `—` in `monthly-maintenance-prompt.md`.
- **Trigger Headers:** Added `[!NOTE]` trigger header to `rules/core-behavioral-compact.md`.

### Added
- **validate-globals.ps1 v4.2.0:** Added `-DryRun` switch for safe-write mode.
- **validate-globals.ps1 v4.2.0:** Added `-GenerateManifest` switch for SHA-256 integrity checking.
- **validate-globals.ps1 v4.2.0:** Added path validation guard and `-Encoding UTF8` on all reads.
- **validate-globals.ps1 v4.2.0:** Added version consistency check across README, CHANGELOG, and script.
- **validate-globals.ps1 v4.2.0:** Improved mojibake detection with broader patterns + Unicode U+FFFD check.
- **validate-globals.ps1 v4.2.0:** Expanded cross-reference regex to cover `ref`, `per`, `in`, and `§N.N` sub-sections.
- **global-roles.md §3:** Added user confirmation step before auto-discovery saves generated files.
- **global-workflow.md:** Moved `llm-behavioral-guidelines.md` from Layer 1 to Layer 2 (on-demand).
- **global-workflow.md:** Added speculative file skip guidance for Layer 3 tech-stack loading.

### Changed
- **.gitignore:** Fixed `.env*` → `.env` + `.env.*` (more precise pattern).
- **.gitignore:** Removed `MEMORY.md` exclusion (now tracked for cross-session value).
- **Layer 0 context size:** Reduced by ~88 lines by moving behavioral guidelines to Layer 2.

## [v4.1.0] - 2026-05-09 - Global Hardening & Deep Scan

### 🚀 Refactoring & Optimization
- **Mojibake Round 2:** Cleared 20+ residual encoding artifacts (`â€—`, `â†'`) across 11 files (Workflows, Tech-stack, Maintenance prompts).
- **Maintenance Consolidation:** Merged redundant content between `update-me.md` and `monthly-maintenance-prompt.md`. `update-me.md` now acts as a high-speed trigger with a pointer to the main checklist.
- **Layer 0 Alignment:** Fixed `README.md` to correctly reflect Layer 0 as `core-behavioral-compact.md` + `global-roles.md`, ensuring architectural truth matches operational workflow.

### 🛡️ Security & Reliability
- **Script Hardening:** Upgraded `validate-globals.ps1` to v4.1.0:
    - Expanded scan scope to include root-level `.md` files.
    - Added **Cross-Reference Validation**: Automated detection of broken `§` section links between files.
    - Added exit code reporting and a detailed scan summary.
- **Git Protection:** Added `.env*` to `.gitignore` to enforce the global "No Secrets" policy by default.
- **Historical Accuracy:** Corrected `MEMORY.md` logs regarding WCAG versions.


## [v4.0.0] — 2026-05-06 — Precision Architecture Enforcement

### Added
- **Filament v4 Architecture Rules:** `tech-stack/filament-4.md` — Cluster organization, Schema pattern, PHP 8.4 property hooks, and repository-specific namespace standards.
- **Mandatory Performance Standards:** Performance and architectural verification checklists added across all rule files.
- **Security Hardening:** Automated verification checklists for zero-trust compliance.

### Changed
- **Method Length Standard:** Aligned to 30-line hard limit across `anti-patterns.md` and `code-quality.md` (previously contradictory: 50 vs 30).
- **$guarded Policy:** Aligned to strict prohibition — `$fillable` only (previously `security-standards.md` implied `$guarded` was acceptable).
- **Principle Naming:** Normalized "THINK FIRST" to "Think Before Coding" across all behavioral files for consistency.
- **Encoding:** Fixed all mojibake artifacts and stripped UTF-8 BOM from 36 files.
- **Validation Script:** `validate-globals.ps1` now writes BOM-less UTF-8 and includes BOM/mojibake detection checks.
- **Workflow Routing:** Added `08-onboarding.md` to Layer 3 routing in `global-workflow.md`.
- **Workflow Steps:** Merged overlapping Steps 5 and 6 into single "VERIFY, VALIDATE & FORMAT" step.

### Fixed
- **vite-7.md:** Corrected PostCSS claim — PostCSS is optional with Tailwind v4, not required.
- **saas-standards.md:** Corrected RLS claim — MySQL does not support native RLS; application-level enforcement required.
- **README.md:** Removed undocumented references (Anime.js, React 19), updated WCAG 2.1 to 2.2, updated system map.
- **Hardcoded paths:** Replaced remaining absolute paths with portable references.

## [v3.5.0] — 2026-05-05 — SaaS Architectural Transformation
### Added
- **SaaS Core Standards:** `rules/saas-standards.md` — Decision matrix for multi-tenancy, data isolation rules, and enterprise compliance.
- **Tenancy Implementation:** `tech-stack/saas-tenancy.md` — Laravel (`stancl/tenancy`) and Next.js patterns for isolated tenant environments.
- **Billing & Subscriptions:** `tech-stack/saas-billing.md` — Global (Stripe) and Regional (MENA) billing integration, usage metering, and feature flags.

### Changed
- **global-workflow.md:** Integrated SaaS standards into Layer 2 (Domain Rules).
- **README.md:** Promoted the SaaS Transformation milestone as a key system capability.

### Removed
- **Formatting Constraints:** Removed the non-negotiable requirement to wrap all English terms in backticks (e.g., `README.md`) within Arabic responses. This simplifies text rendering and returns to standard mixed-language formatting.

## [v3.4.0] — 2026-05-05 — Professionalization & Cleanup
### Changed
- **Branding:** Rebranded the repository as "AI Global OS: The Sovereign Architectural Directive".
- **README.md:** Complete professional rewrite highlighting Layered Loading and Behavioral Sovereignty.
- **Cleanup:** Removed all external attributions (Karpathy references) across the entire system.
- **Visuals:** Removed decorative emoji clutter from core protocol headers to ensure a clean, high-performance interface.

## [v3.3.0] — 2026-05-05 — High-Performance Behavioral Integration
### Added
- **LLM Behavioral Guidelines:** `rules/llm-behavioral-guidelines.md` — 4 principles (Think Before Coding, Simplicity First, Surgical Changes, Goal-Driven Execution) with self-tests.
- **Core Behavioral Compact:** `rules/core-behavioral-compact.md` — Ultra-compact Layer 0 (< 50 lines) loaded on every task.
- **EXAMPLES.md:** Real-world code examples (PHP/Laravel + JS) showing ❌ LLM mistakes vs ✅ correct approaches across all 4 principles.
- **Observable Metrics:** `global-roles.md` §9 — Self-test checklist to verify behavioral guidelines are working.
- **Success Criteria Framework:** `global-workflow.md` Step 4 — Mandatory verifiable goal definition before any code is written.

### Changed
- **global-workflow.md:** Replaced flat "read everything" with **Layered Context Loading** (Layer 0 → Layer 1 → Layer 2 → Layer 3) for context efficiency.
- **global-roles.md:** Added Behavioral Compliance to Quality Gates (§4). Added Observable Metrics (§9).

## [v3.1.0] — 2026-05-02
### Added
- **Design Foundations:** `design-foundations.md` (Bento Grids, Glassmorphism, Neumorphism, Modern Gradients).
- **Responsive UI:** `responsive-ui.md` (Container Queries, Adaptive Layouts, Mobile UX).
- **Accessibility Standards:** `accessibility-standards.md` (WCAG 2.2 AA Compliance).
- **Bilingual Mastery:** `bilingual-mastery.md` (RTL/LTR, Logical Properties, Arabic Typography).

### Changed
- **Global Roles:** `global-roles.md` (Added Font Selection Gate, UI Stack Discovery, and Aesthetics Mandate).
- **Frontend Modern:** `frontend-modern.md` (Added Framer Motion and GSAP animation standards).

## [v3.0.1] — 2026-05-02
### Added
- **New Workflow:** `00-prompt-architecting.md` for refining user prompts before execution.
- **Triggers:** Simplified to a single trigger `/prompt` for the global workflow routing.
- **Role Expansion:** Defined "Prompt Architecting Mode" in `global-roles.md`.


## [v3.0.0] — 2026-05-02
### Added
- **New Tech-Stacks:** `pest-4.md`, `spatie-permission.md`, `spatie-activitylog.md`, `filament-shield.md`, `vite-7.md`, `alpine-3.md`, `postcss-8.md`.
- **New Workflows:** `06-maintenance.md` (System Maintenance), `07-security-audit.md` (Security Audit), `08-onboarding.md` (Project Onboarding).
- **Automation:** `scripts/validate-globals.ps1` for repository hygiene.

### Changed
- **Core Protocols:** `global-roles.md` (added Proactive Auditing), `global-workflow.md` (added Maintenance routing).
- **Rule Hardening:** `security-standards.md`, `performance-standards.md`, `code-quality.md` updated to elite 2026 standards.
- **Tech-Stack Refinement:** Expanded `php-8-4.md`, `mysql-8-4.md`, `filament-4.md`, `laravel-12.md`.
- **Hygiene:** Normalized all file line endings to LF.

## [v2.1.0] — 2026-05-01

### Added
- `rules/anti-patterns.md` — Comprehensive negative constraints & forbidden patterns (7 categories: code structure, error handling, security, performance, database, testing, AI workflow)
- `rules/api-integration-standards.md` — External API integration standards (HTTP client, error handling, retry/resilience, authentication, webhook handling, response caching, versioning)
- `rules/observability-standards.md` — Observability & monitoring standards (structured logging, health endpoints, error tracking, alerting strategy, development observability, audit trails)

### Changed
- `global-roles.md` — Added §8 External Integration & Observability Mandate. Added Anti-Pattern Compliance to §4 Quality Gates.
- `global-workflow.md` — Added Anti-Pattern Cross-Check and External Integration Check to Step 2 (THINK). Updated Base Context list in Step 1 with new rule files.
- `README.md` — Updated repository tree with 3 new rule files.

## [v2.0.0] — 2026-05-01

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

## [v1.0.0] — 2026-05-01

### Added
- Initial repository structure with rules, tech-stack, and workflows
- Core files: global-roles.md, global-workflow.md, update-me.md
- README.md with system documentation
