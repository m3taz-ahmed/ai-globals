# AI Globals Vocabulary & Rules Dictionary
> [!NOTE]
> Central repository of symbolic rules. Referenced globally by codes.

## BEH: Behavioral Rules
- `[BEH-01]`: Think before coding. State assumptions, clarify ambiguities, stop & ask if confused.
- `[BEH-02]`: Simplicity first. Write minimal required code. No speculative abstractions/features.
- `[BEH-03]`: Surgical changes. Touch only requested lines. Match existing style. No drive-by refactoring.
- `[BEH-04]`: Goal-driven execution. Define success criteria first as testable checks. Write test alongside code.

## SEC: Security Standards
- `[SEC-01]`: Zero-trust input validation via FormRequest or strict validator. ⛔ unvalidated inputs.
- `[SEC-02]`: Parameterized queries or Query Builder. ⛔ raw SQL string interpolation (SQLi prevention).
- `[SEC-03]`: Explicit whitelist `$fillable` in models. ⛔ mass-assignment `$guarded = []`.
- `[SEC-04]`: ⛔ log or commit sensitive PII, passwords, tokens, API keys, or `.env` files.
- `[SEC-05]`: Enforce role-based panel access (e.g. Filament Shield). ⛔ hand-rolled RBAC.
- `[SEC-06]`: Sanitize HTML outputs using DOMPurify or escape. ⛔ dangerouslySetInnerHTML with raw user data.
- `[SEC-07]`: Select explicit client DTO projection. ⛔ over-expose database models to client.
- `[SEC-08]`: Encryption at Rest for sensitive fields; Remote storage buckets PRIVATE by default with signed URLs.
- `[SEC-09]`: API Throttling/DDoS: all API routes use rate-limiting middleware, progressive auth lockout.
- `[SEC-10]`: Session/JWT: store JWTs in HttpOnly/Secure cookies (⛔ localStorage), session regenerate on login.
- `[SEC-11]`: Agentic Security: sanitize prompts (Goal Hijacking prevention), mutual auth (mTLS) for M2M/inter-agent, secure UUIDv4 identifiers (⛔ auto-increment IDs).


## PERF: Performance Standards
- `[PERF-01]`: Eager load relationships using `with()`. ⛔ execute queries inside loops (N+1 prevention).
- `[PERF-02]`: Paginate list routes. ⛔ `Model::all()` on tables > 1000 rows.
- `[PERF-03]`: Queue heavy operations (emails, PDFs, external APIs). ⛔ synchronous heavy HTTP execution.
- `[PERF-04]`: Livewire Islands isolated rendering, deferred filters, non-blocking deferred loading.
- `[PERF-05]`: Component state < 50KB. Use Redis cache for larger structures. ⛔ full model serialization in state.
- `[PERF-06]`: Tiered caching (L1 memory, L2 Redis). Key format: `{tenant_id}:{domain}:{entity}:{id}:{variant}`.
- `[PERF-07]`: Cache stampede prevention via atomic locks or early expiration. Compression/igbinary for >1KB.
- `[PERF-08]`: Graceful degradation: circuit breaker falls back to database on cache connection failures.
- `[PERF-09]`: Read/write replica connections routing, transaction connection pooling (PgBouncer/RDS Proxy).
- `[PERF-10]`: Query budget: max 100ms API transaction, 500ms background job. Concurrent index creation.
- `[PERF-11]`: Autovacuum aggressive scale tuning (0.01 vacuum, 0.005 analyze). Table partitioning (>10M rows).


## CODE: Code Quality
- `[CODE-01]`: Service-Repository-Interface separation. Thin controllers call services only.
- `[CODE-02]`: Strict typing: declare `strict_types=1` and explicit return types. ⛔ `mixed` or `any`.
- `[CODE-03]`: Class length < 300 lines, method length < 30 lines. Refactor to focused collaborators.
- `[CODE-04]`: Use Enums or constants for statuses/categories. ⛔ magic strings.
- `[CODE-05]`: SOLID & DRY principles: single responsibility, interface segregation, naming patterns (Services, Actions, DTOs).


## TEST: Testing Standards
- `[TEST-01]`: Mandatory coverage. New features/fixes require corresponding tests.
- `[TEST-02]`: Follow Arrange-Act-Assert (AAA) pattern testing one behavior per test.
- `[TEST-03]`: Use factories/seeders. ⛔ hardcoded IDs, timestamps, or dates in tests.
- `[TEST-04]`: Pest 3+ for Laravel backend; Vitest + `@testing-library/react` (using `userEvent`) for frontend.
- `[TEST-05]`: Playwright E2E with Page Object Model (POM) pattern. ⛔ live API requests in tests (use mocks/fakes).
- `[TEST-06]`: Coverage gates: 80% business logic, 90% APIs, 70% total. ⛔ skip tests without issue.


## GIT: Git Standards
- `[GIT-01]`: Conventional commit format `type(scope): description`. Atomic commits (one logical change).
- `[GIT-02]`: Branch naming conventions: `feature/[id]-[desc]`, `hotfix/[desc]`, `release/[version]`.
- `[GIT-03]`: Protect `main`/`develop` branches. Minimum 1 approval & all CI checks pass. Max PR size ~400 lines.
- `[GIT-04]`: Pipeline-only deploy. Gate production with manual approvals. Use OIDC keyless authentication.
- `[GIT-05]`: Supply chain security: pin third-party Actions by full commit SHA, generate SBOM, sign images (Cosign).


## API: API & Webhooks
- `[API-01]`: timeout default `30s`, connectTimeout `5s`. Encapsulate in dedicated service classes.
- `[API-02]`: Exponential backoff retry (e.g. `->retry(3)`) for 5xx/429. ⛔ retry 4xx errors.
- `[API-03]`: Webhooks signature verification, idempotency checking, raw logging, async processing.
- `[API-04]`: Cache-Retry Interlock: ⛔ retry on cached stale data unless FORCE_REFRESH is sent.
- `[API-05]`: Queue LLM/AI calls via background workers; return immediate ack or stream init. ⛔ synchronous HTTP block.
- `[API-06]`: Stream tokens via Server-Sent Events (SSE); disable Nginx proxy buffering.
- `[API-07]`: Mitigate context collapse: limit tokens with sliding window, semantic injection (RAG), auto-summarization.
- `[API-08]`: Semantic Caching: return cached responses on high vector similarity (>=0.95) to save token cost.
- `[API-09]`: Generative UI Efficiency: Use OpenUI Lang for LLM UI outputs. ⛔ JSON-based UI generation (to reduce tokens by 67% and constrain hallucinations).


## ENV: Windows Environment
- `[ENV-01]`: Explicitly write BOM-less UTF-8 in scripts: `[System.IO.File]::WriteAllText(...)`.
- `[ENV-02]`: PowerShell paths using `\` and quoted. Use WSL 2 for Linux-native tooling.
- `[ENV-03]`: Default line endings to `LF` for cross-platform support.
- `[ENV-04]`: Container-first (FrankenPHP/Octane), Terraform IaC remote state, and GitOps drift reconciliation.


## OBS: Observability & Monitoring
- `[OBS-01]`: Structured (JSON) logging in production; context mandatory. ⛔ logging sensitive data (passwords, tokens, PII).
- `[OBS-02]`: Every app exposes `GET /health` checking database, cache, queue, disk.
- `[OBS-03]`: Capture exceptions via error tracking service (Sentry, etc.); triage within 24h.
- `[OBS-04]`: State-changing operations audited, retention minimum 12 months. ⛔ deleting audit logs.

## SaaS: SaaS & Multi-Tenancy
- `[SaaS-01]`: Shared Schema: every model uses `BelongsToTenant` trait; `tenant_id` indexed.
- `[SaaS-02]`: Separate Schema/DB: provisioning asynchronous (Queue), automated offboarding.
- `[SaaS-03]`: Enterprise: SAML/SSO domain-scoped, RBAC scoped per tenant, activity logs include `tenant_id`.
- `[SaaS-04]`: Gate features by subscription, use webhook for gateway sync.
