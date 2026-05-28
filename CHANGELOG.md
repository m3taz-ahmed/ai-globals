# Changelog

> All notable changes are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/) and [Conventional Commits](https://www.conventionalcommits.org/).
> Historical entries (v1.0.0 to v4.11.0) have been archived to [CHANGELOG-archive.md](file:///D:/server/.ai/CHANGELOG-archive.md).

## [v4.15.0] - 2026-05-28 - Micro-DSL Architecture & 50% Token Optimization 🚀

### Added
- **rules/vocabulary.md:** Centralized symbolic dictionary mapping core rules to lightweight codes (`[BEH-01]`, `[SEC-08]`, `[PERF-06]`).
- **Validation Engine:** Hardened `validate-globals.ps1` and `validate-globals.py` to parse `vocabulary.md` and enforce correct symbolic code usage across the workspace.

### Changed
- **Total Token Reduction:** Achieved a **49.0% reduction** in active context footprint (from ~113,000 to ~57,765 tokens) by archiving legacy logs, implementing scan exclusions, and adopting the Micro-DSL model.
- **Rule Compression:** Rewrote all 21 Layer 0, Layer 1, and Layer 2 rule files (`saas-standards.md`, `security-standards.md`, `caching-standards.md`, etc.) to replace verbose prose with ultra-lean references to the central dictionary.
- **Cross-Platform Hardening:** Validation scripts now dynamically respect `.aiignore` and self-heal missing codes.

---

## [v4.14.0] - 2026-05-27 - Superpowers Methodology & Prompt Architecting Upgrade

### Added
- **useful-repos.md:** Added `VoltAgent/awesome-design-md` to centralize semantic design system contexts.
- **workflows/01-planning.md:** Injected `obra/superpowers` core philosophies (Spec Teasing, Digestible Chunking, and Red/Green TDD & Subagent Execution).
- **workflows/02-execution.md:** Added explicit "Local Skills Delegation" step enforcing usage of `subagent-driven-development` and `tdd-workflows`.

### Changed
- **global-workflow.md:** Mandated `useful-repos.md` scanning in Layer 1 and added the Subagent & TDD execution mandate.
- **workflows/00-prompt-architecting.md:** Upgraded Active Discovery into a strict "Spec Teasing" quality gate preventing code generation before requirement lock-in.
- **rules/anti-patterns.md:** Hardened AI workflow constraints against multi-file execution without local skill delegation.

---

## [v4.13.0] - 2026-05-20 - Multi-Agent Cross-Platform Validation & Saga Protocol

### Added
- **scripts/validate-globals.py:** New cross-platform Python implementation of the validation framework featuring regex + Shannon-entropy based secret scanning.
- **workflows/10-saga-reconciliation.md:** Technical workflow specifying the Saga State Machine and handshake protocols for parallel subagents.

### Changed
- **scripts/validate-globals.ps1:** Upgraded to v4.13.0, modularizing helper functions to be strictly under 30 lines, aligning regex/secret scanning, and optimizing BOM inspection footprint to 3 bytes.
- **scripts/validate-globals.py:** Refactored into granular helper functions under 30 lines, added strict type annotations, and optimized BOM reading footprint.
- **rules/security-standards.md:** Linked Section 8 (Inter-Agent Collaboration Handshake) to workflows/10-saga-reconciliation.md.
- **Documentation:** Synchronized English (README.md) and Arabic (README-AR.md) versions, and updated directory maps/readmes in `rules/README.md`, `tech-stack/README.md`, and `workflows/README.md` to ensure all 11 workflows, 61 tech stack rules, and 18 rule files are fully cataloged.

---

## [v4.12.0] - 2026-05-14 - Laravel 13 & Filament v5 Enterprise Architect Activation

### Added
- **tech-stack/laravel-ai.md:** New canonical standard for the first-party `laravel/ai` SDK (stable, Laravel 13). Covers provider-agnostic LLM interface, RAG/vector search with `pgvector`, AI Agent scaffolding, EDoS rate limiting, streaming SSE responses, and Laravel MCP integration.

### Changed
- **tech-stack/filament-5.md:** Promoted from `[!SPECULATIVE]` to `[!NOTE] STABLE` (released January 2026). Rebuilt around Livewire v4 Islands architecture, deferred filter patterns, model-ID-only state binding, and mandatory 5-method Resource authorization.
- **tech-stack/laravel-13.md:** Expanded to full production standard. Added PHP 8.4 recommendation, AI SDK integration mandate (`laravel/ai`), `Cache::touch()` and JSON:API resource patterns, Context API distributed tracing code example, and compliance checklist.

### Research Basis
- 5 targeted real-time web searches validating: Laravel 13 stable (March 2026), Filament v5 stable (January 2026, Livewire v4 Islands), Laravel AI SDK stable (first-party, provider-agnostic), PHP 8.4 property hooks/asymmetric visibility for DTOs, and FrankenPHP/Octane 2026 production patterns.
