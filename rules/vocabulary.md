[FILE] vocabulary
[OBJ] Dictionary of AI Global symbolic codes.
[RULES]
[BEH]
[BEH-01]: Think before coding.
[BEH-02]: Simplicity first. No speculative features.
[BEH-03]: Surgical changes. Touch ONLY requested lines.
[BEH-04]: Goal-driven execution via tests.

[SEC]
[SEC-01]: Zero-trust validation (FormRequest). No unvalidated inputs.
[SEC-02]: Parameterized queries. No raw SQL interpolation.
[SEC-03]: Whitelist `$fillable`. No `$guarded = []`.
[SEC-04]: No PII/credentials in logs/commits.
[SEC-05]: Enforce RBAC (e.g. Filament Shield).
[SEC-06]: Sanitize HTML outputs (DOMPurify).
[SEC-07]: Explicit DTO projections for client.
[SEC-08]: Encrypt at rest; Private signed URL storage.
[SEC-09]: API Throttling & rate-limiting.
[SEC-10]: JWT in HttpOnly cookies. Regenerate session on login.
[SEC-11]: Agentic mutual auth, UUIDv4, prompt sanitize.

[PERF]
[PERF-01]: Eager load `with()`. No N+1 loops.
[PERF-02]: Paginate >1000 rows.
[PERF-03]: Queue heavy ops.
[PERF-04]: Livewire Islands, deferred filters/loading.
[PERF-05]: Component state <50KB (use Redis for large).
[PERF-06]: Tiered caching (L1/L2) with specific key formats.
[PERF-07]: Stampede prevention via locks. Igbinary compression.
[PERF-08]: Circuit breaker degradation.
[PERF-09]: Read/write replica pools.
[PERF-10]: Query budget: 100ms API, 500ms job.
[PERF-11]: Autovacuum tuning, table partitioning.

[CODE]
[CODE-01]: Service-Repo separation. Thin controllers.
[CODE-02]: Strict typing (`strict_types=1`). No `mixed`.
[CODE-03]: Class <300 lines, method <30 lines. Max 4 args per method (use DTO for 5+).
[CODE-04]: Enums/constants over magic strings.
[CODE-05]: SOLID & DRY.

[TEST]
[TEST-01]: Mandatory coverage.
[TEST-02]: AAA pattern. One behavior per test.
[TEST-03]: Factories/Seeders. No hardcoded IDs/Dates.
[TEST-04]: Pest 3+ (backend), Vitest+RTL (frontend), pytest (Python), go test (Go).
[TEST-05]: Playwright POM. Mocks for external APIs.
[TEST-06]: 80% logic, 90% APIs, 70% total coverage.
[TEST-07]: Two-tier testing: FAST (targeted, ~5s, during iteration) + FULL (complete suite + coverage, before done). See `workflows/testing-tiers.md`.
[TEST-08]: Per-stack commands: PHP `artisan test --filter=` / `artisan test`; JS `vitest run <file>` / `vitest run --coverage`; Python `pytest <file> --no-cov` / `pytest --cov`; Go `go test <pkg> -short` / `go test ./... -cover`.
[TEST-09]: If no test framework exists in the project, write the first test for touched code before declaring done.
[TEST-10]: Mark slow tests (E2E, integration, model-loading, server-startup) with framework skip/group mechanism. Fast tier stays under 5s.

[GIT]
[GIT-01]: Conventional atomic commits.
[GIT-02]: Branches: `feature/*`, `hotfix/*`, `release/*`.
[GIT-03]: Protect `main`. Max PR ~400 lines.
[GIT-04]: Pipeline deploy. OIDC keyless auth.
[GIT-05]: Supply chain security (pin SHAs, SBOM, Cosign).
[GIT-06]: No `git add .` or `git add -A`. Stage only files YOU modified with `git add <file>`. No destructive git without user approval.

[API]
[API-01]: Timeout 30s, connect 5s.
[API-02]: Expo backoff retry for 5xx/429. No 4xx retries.
[API-03]: Webhook signature & idempotency.
[API-04]: Interlock cache retries.
[API-05]: Queue LLM calls. SSE for streams.
[API-06]: Disable Nginx buffering for SSE.
[API-07]: Sliding window token limit & RAG.
[API-08]: Semantic vector caching (0.95).
[API-09]: OpenUI Lang. No JSON UI.

[ENV]
[ENV-01]: BOM-less UTF-8 via `[System.IO.File]`.
[ENV-02]: PowerShell quotes/slashes. WSL2.
[ENV-03]: LF line endings.
[ENV-04]: Container-first (Octane), Terraform.

[OBS]
[OBS-01]: JSON logging with context. No PII.
[OBS-02]: Expose `/health`.
[OBS-03]: Sentry error tracking.
[OBS-04]: State-changing audit logs (12mo retention).

[VER]
[VER-01]: Detect exact package version from lockfile before loading `tech-stack/<pkg>-<ver>.md`. No defaults.

[SaaS]
[SaaS-01]: Shared DB: `BelongsToTenant` trait.
[SaaS-02]: Separate DB: Async provision.
[SaaS-03]: Enterprise: SAML/SSO, Tenant RBAC.
[SaaS-04]: Gate features via subscriptions.

[ARCH]
[ARCH-01]: No folklore engineering. Name the problem before the pattern. No interface without a client/contract/boundary. No "Clean Architecture" by folder shape â€” inspect dependency direction. No "well-architected" by managed services â€” review flows/failure/security/cost/ops/perf.
[ARCH-02]: No source-only runtime inference when optimization/concurrency/generated code/native boundaries are relevant. Capture the effective execution contract.
[ARCH-03]: No multi-variable debugging experiments unless the result remains discriminating.
[ARCH-04]: No passing-test-as-proof when the test cannot observe the claimed failure class.
[ARCH-05]: No hidden accepted risk. Record consequence, owner, expiry, and trigger for reconsideration.
[ARCH-06]: No governance theater. Controls must exist in measurable runtime evidence, not only documents. A policy check that runs only after user-visible output is governance theater.
[ARCH-07]: No ambient authority. The model may propose; only an independent control plane authorizes consequence. A policy decision cannot be reused across targets. Tool output is untrusted until revalidated at the next boundary.

[DIR]
[DIR-01]: Working directory is D:\server\.ai ONLY. D:\server\aizee is READ-ONLY (deployment/usage folder, updated only via batch script). All edits go in .ai.
