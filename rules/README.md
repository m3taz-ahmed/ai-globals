# `rules/` — Precision-Guided Constraints

This directory contains the **architectural law** of the system. Every file here is a hard constraint that the AI agent **must** comply with. They are not suggestions.

## Loading Strategy (Layered Context)

Rules are loaded in a strict priority order to minimize context window usage:

| Layer | Files | When Loaded |
|---|---|---|
| **Layer 0** | `core-behavioral-compact.md`, `global-roles.md` | **Always** — every single task |
| **Layer 1** | `anti-patterns.md` | **Always** — hard-stop constraints |
| **Layer 2** | All others | **On-demand** — only when the task requires it |

> [!IMPORTANT]
> Do NOT load all rule files on every task. The lazy-loading pattern is what keeps the system fast and context-efficient.

## File Reference

| File | Domain | Purpose |
|---|---|---|
| `core-behavioral-compact.md` | Behavior | 4 non-negotiable principles in < 50 lines |
| `anti-patterns.md` | Safety | Everything the AI must NEVER do |
| `principal-architect.md` | Identity | Persona, decision-making authority, architectural DNA |
| `security-standards.md` | Security | OWASP-driven Zero-Trust protocols |
| `performance-standards.md` | Performance | N+1 prevention, query budgets, caching strategy |
| `api-integration-standards.md` | API | Circuit breakers, retry logic, idempotency |
| `ai-integration-standards.md` | AI | Asynchronous AI queues, SSE streaming, Context Compaction |
| `observability-standards.md` | Ops | Structured logging, health endpoints, audit trails |
| `code-quality.md` | Quality | SOLID, DRY, KISS, naming conventions |
| `git-standards.md` | Git | Conventional Commits, branching, PR standards |
| `saas-standards.md` | SaaS | Multi-tenancy decision matrix, billing core |
| `llm-behavioral-guidelines.md` | Behavior | Expanded self-tests for behavioral compliance |
| `environment-windows.md` | DevEnv | Windows/WSL/PowerShell compatibility rules |
| `env-management-standards.md` | DevEnv | Strict synchronization protocols for .env files across staging/prod |
| `caching-standards.md` | Caching | L1/L2 topology, Redis HA, stampede prevention, serialization |
| `ci-cd-standards.md` | CI/CD | SLSA Level 3, OIDC keyless auth, SBOM, supply chain security |
| `database-scaling.md` | Database | PG17 tuning, read replicas, connection pooling, vacuum strategy |
| `devops-standards.md` | DevOps | Progressive delivery, chaos engineering, GitOps, self-healing |
| `testing-standards.md` | Testing | Test pyramid, Pest/Vitest/Playwright, TDD, coverage enforcement |

## Contributing a New Rule

See [CONTRIBUTING.md](../CONTRIBUTING.md) for the full process. Key points:
- Every rule must have a concrete ❌/✅ example
- Rules must not contradict each other — resolve conflicts explicitly
- Run `validate-globals.ps1` after any change to check cross-references
