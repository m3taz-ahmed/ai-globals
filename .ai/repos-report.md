# aiZee — Repository Study Report

- **Date**: 2026-08-06
- **Method**: `git clone --depth 1` into `temp/repos-study/`, then architecture analysis.
- **Cloned**: 31 of 32 listed repositories.
- **Failed**: `mnemopay/praetor` (repository not found on GitHub).

---

## 1. Agent operating systems / governance

### RightNow-AI/openfang
- **Category**: Agent operating systems / governance
- **Summary**: Rust-based Agent OS with 14 crates compiling to a single 32MB binary. Core innovation is "Hands" — pre-built autonomous capability packages (Clip, Lead, Collector, Predictor, Researcher, Twitter, Browser) that run on schedules without prompting. Includes built-in dashboard, MCP integration, WASM sandboxing, and peer-to-peer networking via OFP protocol.
- **Top takeaways**:
  - Hands pattern: HAND.toml manifest + system prompt + SKILL.md + guardrails = compiled autonomous agent
  - Single-binary deployment with embedded SQLite, no Docker or runtime deps
  - KernelHandle trait pattern for decoupling runtime from kernel
  - WASM sandbox for untrusted code execution
  - OFP (OpenFang Protocol) for P2P agent discovery and task delegation
- **Adopt?**: HOLD
- **Why?**: Strong architecture and performance (180ms cold start, 40MB idle), but Rust-based and monolithic. aiZee is Python-first; adopting would require significant rewrite or subprocess integration. Hands pattern is reusable but the implementation is tightly coupled to Rust ecosystem.
- **Effort**: large
- **Target component**: runtime/ (if adopting pattern), otherwise reference only

### shackleai/orchestrator
- **Category**: Agent operating systems / governance
- **Summary**: TypeScript/Node.js orchestrator that structures multi-agent systems like a company org chart. Features: companies (org units), agents with roles (CEO/Manager/Worker), GitHub-style task tracker, default-deny governance engine with glob-pattern tool access control, per-agent monthly budgets, cron heartbeat scheduling, and 6 execution adapters (Process, HTTP, Claude Code, MCP, OpenClaw, CrewAI). Local-first with embedded PGlite or PostgreSQL.
- **Top takeaways**:
  - Default-deny governance with glob-pattern tool access control and priority resolution
  - Per-agent + per-company monthly budget tracking with 80% alert / 100% hard stop
  - Org-chart hierarchy (CEO → Manager → Worker) for task routing
  - Adapter pattern for pluggable execution backends
  - Immutable activity log for audit trail
- **Adopt?**: YES
- **Why?**: TypeScript aligns with aiZee stack (has Node.js components). Governance engine and budget tracking are directly applicable to aios_mcp/. Adapter pattern matches aiZee's plugin architecture. MIT license, active maintenance (March 2026).
- **Effort**: medium
- **Target component**: rules/, aios_mcp/

### Justin0504/Sovereign-OS
- **Category**: Agent operating systems / governance
- **Summary**: Python-based autonomous corporation framework with Charter-driven governance. Single YAML Charter declares mission, spending limits, KPIs, and allowed capabilities. Architecture: Charter → CEO (plan) → CFO (approve budget) → Workers (execute) → Auditor (verify against KPIs) → Ledger (append-only accounting). Features TrustScore capability gating, JIT leases for high-risk ops, 16 built-in workers, marketplace oversight (inbound task ingestion from TaskBounty/StacksTasker/BotBounty, outbound escrow via RentAHuman), and x402 APB bounty discovery.
- **Top takeaways**:
  - Charter as single source of truth — all behavior flows from YAML config
  - TrustScore-based capability gating with JIT leases (zero standing privilege)
  - Auditor with category-tuned rubrics and signed AuditReports
  - Append-only UnifiedLedger for USD + token accounting
  - Task-category backbone mapping categories to workers, budget ceilings, and connectors
- **Adopt?**: YES
- **Why?**: Python-first matches aiZee stack. Charter pattern is excellent for declarative agent configuration. TrustScore + JIT leases address aiZee's runtime gate requirements. Marketplace oversight bridges external task platforms. MIT license, very active (July 2026).
- **Effort**: medium
- **Target component**: runtime/, rules/, aios_mcp/

### microsoft/agent-governance-toolkit
- **Category**: Agent operating systems / governance
- **Summary**: Microsoft's multi-language governance toolkit for runtime policy enforcement, zero-trust identity, sandboxing, and SRE. Intercepts every tool call/message/delegation in deterministic code before model intent reaches the wire. Policy-as-YAML with `govern()` decorator, AgentControl API, multi-language SDKs (Python, TypeScript, .NET, Rust, Go), MCP server integration, and comprehensive compliance (OWASP Agentic Top 10, AARM, ATF). Monorepo with 40+ packages including policy engine, trust layer, hypervisor, and framework integrations (LangChain, CrewAI, AutoGen, etc.).
- **Top takeaways**:
  - Deterministic application-layer enforcement (not prompt-level safety)
  - Policy-as-YAML with condition/action/approval model
  - Multi-language SDKs with consistent governance surface
  - AgentMesh trust layer: Ed25519 identity, 5-dimension trust scoring, DID (did:mesh)
  - Comprehensive compliance coverage and Microsoft-backed governance
- **Adopt?**: YES
- **Why?**: Best-in-class governance with enterprise-grade compliance. Multi-language support matches aiZee's polyglot needs. Policy engine and trust layer are directly reusable. Microsoft backing ensures long-term maintenance. MIT license, very active (August 2026).
- **Effort**: medium
- **Target component**: rules/, runtime/, aios_mcp/

### preloop/preloop
- **Category**: Agent operating systems / governance
- **Summary**: Full-stack control plane with MCP firewall, OpenAI/Anthropic-compatible model gateway, policy-as-code (YAML+CEL), human approvals, and session observability. FastAPI backend, Lit frontend, PostgreSQL+PGVector, NATS event bus. Discovers and onboards existing agents (Claude Code, Cursor, OpenClaw, etc.) via CLI, rewriting configs to route through Preloop's enforcement layer.
- **Top takeaways**:
  - Policy-as-code with YAML import/export, versioning, rollback, and diff preview
  - Model gateway with per-account/flow budgets, token accounting, and attribution
  - Human approval workflows (mobile, Slack, email, webhook) with async-safe decisions
  - MCP firewall: allow/deny/approve tool calls with CEL expressions
  - Runtime plugin system for live agent control (OpenClaw, Hermes)
- **Adopt?**: YES
- **Why?**: Mature, actively maintained (commit 2026-08-06), MIT-licensed. Policy engine and model gateway patterns directly applicable to aiZee runtime governance. MCP firewall aligns with aios_mcp work. NATS+worker pattern for flow execution matches our async architecture needs.
- **Effort**: medium
- **Target component**: runtime/, aios_mcp/, rules/

### nanny-run/nanny
- **Category**: Agent operating systems / governance
- **Summary**: Deterministic enforcement primitive. Parent-process model: `nanny run` spawns agent as child, enforces hard limits (steps, tokens, timeout) via internal bridge. Rust CLI + Python SDK. No grace periods, no recovery—process killed on limit breach. Supports local bridge (Unix socket/TCP) and governance server (mTLS) for cross-machine enforcement.
- **Top takeaways**:
  - Parent-child process enforcement: structurally impossible for agent to bypass
  - Three independent limits: timeout (wall-clock), steps (tool calls), tokens (budget)
  - Tool allowlist + custom rules (code, not config) evaluated on every call
  - Agent scopes: per-role limits with inheritance (inner cannot exceed outer)
  - Direct-call pattern: code drives tool calls, LLM only reasons—model-agnostic
- **Adopt?**: HOLD
- **Why?**: Excellent primitive for hard limits, but enforcement model is process-level (parent-child). aiZee needs in-process governance for kernel.py routing, not process spawning. SDK patterns (tool decorators, rule functions) are reusable for our policy engine, but the CLI/runtime-plugin approach doesn't fit our architecture.
- **Effort**: small
- **Target component**: rules/ (pattern extraction only)

### ViktorWelbers/paddock
- **Category**: Agent operating systems / governance
- **Summary**: Self-hosted governance plane for coding agents on Kubernetes. Spawns per-user sandboxes (pods) with no real keys, egress only through gateway. Three Go binaries: server (control plane, SQLite), gateway (model proxy + egress CONNECT proxy), CLI. Hierarchical budgets (org→team→user→session), OPA/Rego policies, append-only audit log. Supports in-pod and local-harness modes.
- **Top takeaways**:
  - Hierarchical budget ledger with ancestor exhaustion checks
  - Gateway proxy: authenticates session tokens, injects real keys, meters usage
  - Governed egress: CONNECT proxy with domain allowlist and OPA decisions
  - Server-side MCP: central registry, credentials injected at gateway
  - Sandboxes powerless by construction: no service-account token, no secrets
- **Adopt?**: HOLD
- **Why?**: Kubernetes-specific (sandboxes, pods, NetworkPolicy). aiZee is not K8s-native. Budget ledger and gateway proxy patterns are valuable, but the sandbox isolation model doesn't translate. OPA integration is worth studying for our policy engine, but full adoption would require significant architectural drift.
- **Effort**: large
- **Target component**: rules/ (budget ledger pattern only)

### mnemopay/praetor
- **Category**: Agent operating systems / governance
- **Summary**: Repository not found at `https://github.com/mnemopay/praetor.git`.
- **Top takeaways**: N/A
- **Adopt?**: NO
- **Why?**: Clone failed with "Repository not found". Possibly private, renamed, or removed.
- **Effort**: N/A
- **Target component**: N/A

---

## 2. MCP orchestration

### lastmile-ai/mcp-agent
- **Category**: MCP orchestration
- **Summary**: Python framework for building effective agents with MCP using composable patterns. Implements Anthropic's agent patterns (map-reduce, orchestrator, evaluator-optimizer, router) with full MCP support and Temporal-based durable execution for production workflows.
- **Top takeaways**:
  - Composable workflow patterns with decorator-based task registration
  - Full MCP lifecycle management (tools, resources, prompts, OAuth, sampling, roots)
  - Temporal integration for durable execution without API changes
  - Agent-as-MCP-server pattern for exposing agents as servers
  - Built-in observability with OpenTelemetry tracing
- **Adopt?**: YES
- **Why?**: Mature, well-documented framework with production-ready patterns. Composable design aligns with aiZee's modular architecture. Temporal support provides robust execution backend.
- **Effort**: medium
- **Target component**: runtime/orchestrator/

### mrorigo/mcp-orchestrator
- **Category**: MCP orchestration
- **Summary**: TypeScript library pioneering "Code Mode" - lets LLMs write and execute TypeScript code using MCP tools as APIs, achieving 60-75% token reduction for multi-step workflows. Includes VM sandboxing, snippet system for code reuse, and native A2A protocol bridge.
- **Top takeaways**:
  - Code Mode: LLM generates TypeScript instead of tool calls, chains operations without round-trips
  - VM-based secure sandbox with timeout enforcement
  - Snippet system promotes generated code to reusable MCP tools
  - A2A bridge exposes orchestrated experts as agent servers
  - Flexible execution: code mode, tool calling, or LLM sampling per task
- **Adopt?**: YES
- **Why?**: Innovative Code Mode pattern reduces token costs significantly. A2A bridge enables multi-agent collaboration. TypeScript aligns with aiZee frontend/runtime stack.
- **Effort**: medium
- **Target component**: runtime/codemode/, aios_mcp/

### musaceylan/OrchestrAI
- **Category**: MCP orchestration
- **Summary**: MCP-native multi-model orchestration server that routes software engineering tasks across specialist models (Anthropic, OpenAI, Gemini, local). Implements role-based routing (Planner, Coder, Tester, Reviewer, Judge) with privacy tiers and full artifact provenance.
- **Top takeaways**:
  - Role-based routing engine assigns tasks to best-fit models per capability
  - Orchestration modes: planner_coder_reviewer, parallel_draft, impl_tester
  - Privacy tiers (secret → local only, confidential → enterprise, internal, public)
  - Built-in verification: lint, test, type-check runners
  - Full artifact + trace system with provenance tracking
- **Adopt?**: HOLD
- **Why?**: Strong multi-model routing concept but early-stage (v0.1.0). Privacy tiers and verification valuable, but may duplicate aiZee policy engine. Monitor for maturity.
- **Effort**: large
- **Target component**: runtime/router/, policies/

### chrisnewell91/Meta-MCP-Server
- **Category**: MCP orchestration
- **Summary**: Meta-MCP server that dynamically spawns and manages child MCP servers on-demand. Features server pooling (100x reuse performance), security hardening (command whitelisting, path sanitization), health monitoring, and event audit trails.
- **Top takeaways**:
  - Dynamic server spawning from templates or existing scripts
  - Server pooling for massive performance improvement on reuse
  - Security: command validation, path sanitization, resource limits
  - Health monitoring with uptime, idle time, resource tracking
  - Event system with comprehensive audit trail
- **Adopt?**: NO
- **Why?**: Meta-server pattern is useful but aiZee likely needs direct orchestration rather than spawning child processes. Pooling concept reusable but implementation is process-heavy.
- **Effort**: medium
- **Target component**: runtime/pooling/ (concepts only)

### dufangshi/orchestration-mcp
- **Category**: MCP orchestration
- **Summary**: TypeScript MCP server providing stable tool surface for launching/tracking external coding-agent runs. Backend-agnostic adapter pattern supports local Codex, Claude Code, or remote A2A agents while maintaining consistent MCP interface.
- **Top takeaways**:
  - Backend-agnostic adapter pattern (codex, claude_code, remote_a2a)
  - Stable MCP surface while execution backend swappable
  - Event-based polling with artifact storage for large payloads
  - Session management with resume capability
  - Profile system for persona/job-description injection
- **Adopt?**: YES
- **Why?**: Adapter pattern exactly matches aiZee need for backend-agnostic agent execution. Clean separation between MCP surface and execution backends.
- **Effort**: small
- **Target component**: aios_mcp/adapters/, runtime/agent-runtime/

---

## 3. Policy / rule engines

### open-policy-agent/opa
- **Category**: Policy / rule engines
- **Summary**: CNCF-graduated general-purpose policy engine written in Go with Rego language. Provides unified, context-aware policy enforcement across entire stack via REST API, Go SDK, or standalone server mode. Supports Kubernetes, Terraform, Docker, SSH integration with WASM compilation for edge deployment.
- **Top takeaways**:
  - Declarative Rego language with partial evaluation and built-in conflict resolution
  - Bundle-based policy distribution with signing and automatic polling
  - Multi-language integration via REST API, Go SDK, and WASM targets
  - Mature ecosystem with CNCF graduation, security audit, and extensive adopters
  - Decision logging, status reporting, and external data integration
- **Adopt?**: HOLD
- **Why?**: Overkill for aiZee runtime policies. Heavy Go dependency, complex Rego learning curve, designed for cloud-native infrastructure (K8s, Terraform) not agent runtime governance. Better fit for infrastructure-as-code policies.
- **Effort**: large
- **Target component**: infrastructure/policies/

### MAIF/arta
- **Category**: Policy / rule engines
- **Summary**: Python rules engine focused on business rules maintainability. Rules defined in YAML, separated from codebase, with Python action modules. Designed to centralize and standardize deterministic rules, particularly for ML projects combining with model predictions.
- **Top takeaways**:
  - YAML-based rule definitions with Python action modules
  - Rule sets and groups for organizing business logic
  - Simple and standard conditions with validation functions
  - 94% test coverage, Apache 2.0 license
  - Designed for Python developers, minimal learning curve
- **Adopt?**: HOLD
- **Why?**: Too domain-specific for business rules/ML pipelines. Lacks agent-specific features (tool governance, approval signals, risk-based decisions). Better for ML feature engineering or email classification, not runtime agent control.
- **Effort**: medium
- **Target component**: ml/rules/

### poyao0705/guardian-angel
- **Category**: Policy / rule engines
- **Summary**: Lightweight Python SDK for governing AI agent tool execution. Intercepts agent actions, evaluates YAML/JSON policies, returns allow/deny/require_approval before tool runs. First-match rule semantics, configurable safety modes, approval signal for human-in-the-loop workflows.
- **Top takeaways**:
  - Purpose-built for AI agent tool governance with predicate rules
  - Approval signal via ApprovalRequiredError for framework integration
  - Safety modes: default decision, evaluation error behavior, protected tools
  - CLI with --explain and --verbose for debugging
  - invoke/ainvoke for policy enforcement on any function without decorators
- **Adopt?**: YES
- **Why?**: Perfect fit for aiZee runtime kernel. Designed specifically for agent tool governance, has approval workflow integration, lightweight Python with no heavy dependencies. Matches runtime/policies/ requirements exactly.
- **Effort**: small
- **Target component**: runtime/policies/

### JonSil89/gatehouse-policy-engine
- **Category**: Policy / rule engines
- **Summary**: ISO 27001-based policy validation engine for infrastructure changes. Three-gate system: automated validation (CI/CD), manual review (risk-based approvers), deployment conditions (time windows). Risk classes 1-3 determine approval requirements. Finnish-language templates for change requests.
- **Top takeaways**:
  - Three-gate quality system with risk-based approval workflows
  - ISO 27001 mapping (A.12.1.2, A.14.2.2, A.12.4.1)
  - Python validation scripts with regex-based rule checking
  - Markdown-based change request templates
  - CI/CD integration with JSON output for automated gates
- **Adopt?**: NO
- **Why?**: Domain-specific for infrastructure change management, not agent runtime. Finnish-language hardcoded, risk classes tied to manual review processes, no agent-specific concepts. Better for DevOps change approval workflows.
- **Effort**: medium
- **Target component**: infrastructure/change-management/

### SemClone/ospac
- **Category**: Policy / rule engines
- **Summary**: OSS license compliance policy engine with JSON-first architecture. Evaluates licenses against policies using 712 SPDX licenses with compatibility matrices and obligation tracking. Build target templates for mobile, desktop, web, server, embedded. MCP-ready with JSON output.
- **Top takeaways**:
  - JSON dataset with 712 SPDX licenses and compatibility matrices
  - Policy as code with versionable YAML/JSON definitions
  - Obligation tracking with remediation data
  - Build target policies (mobile, desktop, web, server, embedded)
  - Dual licensing: Apache-2.0 code, CC BY-NC-SA 4.0 dataset (non-commercial)
- **Adopt?**: NO
- **Why?**: Domain-specific for license compliance, not agent governance. Dataset license restricts commercial use (CC BY-NC-SA 4.0), which conflicts with aiZee commercial deployment. No agent runtime concepts.
- **Effort**: medium
- **Target component**: legal/compliance/

---

## 4. Coding guardrails

### fjb040911/ai-rules
- **Category**: Coding guardrails
- **Summary**: Rule-aware CLI that compiles Markdown rules into structured Rule IR, local evidence, and deterministic audit/fix prompts. Evolving toward a rules compiler for AI coding workflows with AST-backed evidence for frontend rules.
- **Top takeaways**:
  - Rule compilation from Markdown to structured IR with validator artifacts
  - Template inheritance system (base + branch) for multi-stack support
  - AST-backed local evidence for JS/TS/Vue rules via Babel/Vue compiler
  - Logic risk inspection mode for business-logic vulnerabilities
  - Path aliases and exception handling for non-standard repo layouts
- **Adopt?**: YES
- **Why?**: Directly aligns with aiZee's rule compilation needs. CLI tool integrates easily into existing workflows. Template system matches multi-stack requirements. Logic inspection adds security value.
- **Effort**: small
- **Target component**: rules/, runtime/

### yunbow/ai-dev-os
- **Category**: Coding guardrails
- **Summary**: Theoretical framework organizing coding rules into 4 lifespan layers (Philosophy, Decision Criteria, Guidelines, AI Frames) with specificity cascade for conflict resolution. Emphasizes tool independence and rule harvesting from real code reviews.
- **Top takeaways**:
  - 4-layer model separating stable principles (L1-L2) from volatile tool configs (L4)
  - Specificity cascade for rule conflict resolution (framework > common > project > criteria > philosophy)
  - Two-tier context strategy: minimal static context (~8K tokens) + comprehensive dynamic checks
  - Rule harvesting methodology: code → review gaps → extract guidelines
  - Tool independence preserves 75% of rules across agent migrations
- **Adopt?**: HOLD
- **Why?**: Strong theoretical foundation but requires adopting entire framework structure. aiZee already has rule organization; may conflict with existing architecture. Best for inspiration, not direct adoption.
- **Effort**: medium
- **Target component**: rules/ (conceptual)

### nizos/probity
- **Category**: Coding guardrails
- **Summary**: Runtime guardrail engine that intercepts agent file writes and shell commands before execution. Blocks violations with deterministic patterns or AI-validated rules using vendor SDKs. Per-vendor adapter pattern with session transcript reading.
- **Top takeaways**:
  - Per-vendor adapter anti-corruption layer (Claude Code, Codex, Copilot)
  - Session transcript reading for context-aware rule evaluation
  - Custom rule DSL with sync/async support and context access
  - Fast-path optimization for single-test writes using ast-grep
  - AI validation piggybacks on agent's existing authentication
- **Adopt?**: YES
- **Why?**: Runtime enforcement matches aiZee's kernel.py gate model. Adapter pattern is reusable for multi-agent support. Custom rule DSL flexible for project-specific policies. Active maintenance with good test coverage.
- **Effort**: medium
- **Target component**: runtime/kernel.py

### stawils/coding-guardrails
- **Category**: Coding guardrails
- **Summary**: Two-layer proxy (Forge reliability + 13 guardrail rules) between coding agent and local LLM. Blocks path traversal, destructive commands, network egress, secret exfiltration. Stateful rules for loop detection, session budgets, sequencing.
- **Top takeaways**:
  - Rule protocol with allow/block/nudge actions and composable design
  - Prefix matching for tool names works across agents without per-agent config
  - Stateful rules track history (prerequisites, sequencing, loop detection)
  - Lint gate integration (ruff/biome/gofmt) blocks defects from local models
  - Layer 1 Forge handles rescue parsing, validation, retries for tool calling
- **Adopt?**: HOLD
- **Why?**: Designed for local LLM proxy architecture, not cloud-first aiZee. Python-based but requires llama-server backend. Rule protocol is reusable but full proxy integration would duplicate existing infrastructure.
- **Effort**: large
- **Target component**: runtime/ (if adopting local LLM path)

### xianzuyang9-blip/agent-guardrails
- **Category**: Coding guardrails
- **Summary**: Policy engine for intercepting tool calls before execution with pattern-based rule packs. Promises block/suggest/redact/confirm actions. Currently minimal implementation with only README and package.json stub.
- **Top takeaways**:
  - Pattern-based policy engine concept
  - Multi-action resolution (block, suggest, redact, confirm)
  - YAML rule packs (planned, not implemented)
  - Match-and-resolve API design
- **Adopt?**: NO
- **Why?**: Project is essentially empty - no source code, no implementation, no documentation. Only README with placeholder API. Last commit June 2026 with minimal activity. Not usable in current state.
- **Effort**: large (would require building from scratch)
- **Target component**: N/A

---

## 5. Memory / RAG / knowledge graph

### neo4j-labs/agent-memory
- **Category**: Memory / RAG / knowledge graph
- **Summary**: Graph-native memory system for AI agents backed by Neo4j with Python/TypeScript SDKs. Three memory types (short-term, long-term, reasoning) with POLE+O knowledge graph model, multi-stage entity extraction, MCP server with 16 tools, and both hosted NAMS service and self-hosted Neo4j bolt options.
- **Top takeaways**:
  - POLE+O graph model for entity resolution and knowledge graph construction
  - Provider abstraction supporting 100+ LLM/embedding providers via LiteLLM
  - MCP server with 16 tools for Claude Desktop/Cursor integration
  - Buffered writes, consolidation primitives, and audit trails for production
  - Cross-language SDKs (Python + TypeScript) with TCK conformance testing
- **Adopt?**: HOLD
- **Why?**: Strong Neo4j lock-in. Good for graph-heavy workloads but requires Neo4j infrastructure. Hosted NAMS reduces friction but adds external dependency. Consider if aiZee needs graph-native memory vs simpler storage.
- **Effort**: medium
- **Target component**: memory/

### PlateerLab/synaptic-memory
- **Category**: Memory / RAG / knowledge graph
- **Summary**: Zero LLM cost at index time graph + MCP tool server with hybrid retrieval, CDC-based live database sync, and Korean FTS. Deterministic extraction from structure (FKs, categories, chunk order) without LLM calls during indexing. Supports SQLite, PostgreSQL, Kuzu, Qdrant, MinIO backends.
- **Top takeaways**:
  - Zero LLM indexing cost - relations extracted from structure, not LLM
  - CDC sync for live databases (SQLite, PostgreSQL, MySQL/MariaDB)
  - 36 MCP tools for multi-turn agent exploration
  - Backend protocol for pluggable storage (SQLite, PostgreSQL, Kuzu, composite)
  - DomainProfile TOML for domain-specific ontology injection
- **Adopt?**: YES
- **Why?**: Zero lock-in, zero LLM indexing cost, deterministic extraction fits sovereign OS principles. CDC sync is valuable for live data. MCP-native with extensive tooling. Apache 2.0 with active maintenance.
- **Effort**: small
- **Target component**: memory/, graphify-out/

### mtrnix/metronix-memory
- **Category**: Memory / RAG / knowledge graph
- **Summary**: Self-hosted memory infra with Docker stack (PostgreSQL, Qdrant, Neo4j, Redis). Hybrid RAG with dense + sparse + graph retrieval, temporal knowledge graph, freshness checks, agent-scoped context. MCP-native, local-model friendly with Ollama integration. Benchmarks show strong retrieval performance.
- **Top takeaways**:
  - Strict 6-layer architecture (L0-L6) with one-way dependencies
  - Freshness pipeline to detect stale/conflicting memory
  - Hybrid retrieval: dense vectors + SPLADE sparse + graph context
  - Agent/workspace scoping with RBAC
  - Docker-compose deployment with 6GB+ RAM requirement
- **Adopt?**: HOLD
- **Why?**: Heavy infrastructure footprint (4 databases). Good for dedicated memory service but overkill for embedded OS memory. Consider extracting retrieval algorithms if needed, but full stack is too large.
- **Effort**: large
- **Target component**: runtime/ (as optional service)

### XMUDeepLIT/MemGraphRAG
- **Category**: Memory / RAG / knowledge graph
- **Summary**: Research framework for memory-enhanced GraphRAG with three-layer memory (schema, fact, passage layers). Ontology induction, conflict-aware construction, graph-enhanced retrieval with embedding similarity + Personalized PageRank. Academic project accepted to KDD'26.
- **Top takeaways**:
  - Three-layer memory with bidirectional schema-fact-passage links
  - Ontology induction to abstract facts into reusable schemas
  - Conflict detection and resolution with passage evidence
  - Batch QA with metrics (recall, latency, token usage)
  - Research codebase - not production-ready
- **Adopt?**: NO
- **Why?**: Academic research code, not production-ready. Complex pipeline focused on paper reproduction rather than OS integration. Better to extract ideas (three-layer memory, conflict resolution) than adopt wholesale.
- **Effort**: large
- **Target component**: N/A (research reference only)

### MemMachine/MemMachine
- **Category**: Memory / RAG / knowledge graph
- **Summary**: Long-term memory layer for AI agents with episodic (graph-based conversational), profile (SQL user facts), and working (short-term) memory. Python/TypeScript SDKs, REST API, MCP server, integrations with LangChain, LangGraph, CrewAI, LlamaIndex, AWS Strands, n8n, Dify, FastGPT.
- **Top takeaways**:
  - Three memory types: episodic (Neo4j graph), profile (SQL), working (session)
  - Extensive framework integrations (9+ major frameworks)
  - MCP server (stdio + HTTP modes)
  - Project/org/group/agent/user/session scoping
  - Self-hosted or cloud options with Apache 2.0 license
- **Adopt?**: HOLD
- **Why?**: Good abstraction but requires separate server deployment. Neo4j + SQL dual storage adds complexity. Consider if multi-framework integration is needed for aiZee or if simpler memory suffices.
- **Effort**: medium
- **Target component**: memory/ (if multi-framework support needed)

---

## 6. Dashboard / UI design

### facebook/astryx
- **Category**: Dashboard / UI design
- **Summary**: Meta's open-source design system built on React 19+ and StyleX. Ships 150+ accessible components, 7 themes, CLI tooling, and page templates. Designed for both humans and AI agents with open internals, no styling lock-in (CSS custom properties), and comprehensive documentation via Storybook.
- **Top takeaways**:
  - Open component architecture with swizzle for deep customization without forking
  - Theme system via CSS custom property overrides - no wrapper components needed
  - CLI provides component discovery, docs, templates, and codemods for AI agents
  - No build plugins required - ships pre-built CSS that works with Tailwind, CSS modules, or plain CSS
  - AI/human parity: same API and tooling for both people and coding assistants
- **Adopt?**: YES
- **Why?**: React 19 requirement aligns with modern stack, MIT license, active Meta maintenance, zero styling lock-in, and AI-agent-friendly CLI make it ideal for aiZee dashboard/frontend work.
- **Effort**: medium
- **Target component**: dashboard/, frontend/

### VoltAgent/awesome-design-md
- **Category**: Dashboard / UI design
- **Summary**: Curated collection of 73+ DESIGN.md files extracted from real websites (Claude, Linear, Vercel, etc.). Each file captures a complete visual language in Google Stitch's markdown format with YAML frontmatter for colors, typography, spacing, and component tokens. AI agents read these to generate consistent UI.
- **Top takeaways**:
  - DESIGN.md format: plain markdown with YAML frontmatter for design tokens
  - Token structure: colors, typography, rounded, spacing, components with reference syntax
  - Drop-in integration: copy file to project root, AI agents instantly understand design language
  - Real-world patterns: analyzed from production sites (Linear, Claude, Vercel, Supabase, etc.)
  - Request service: can commission custom DESIGN.md for specific sites
- **Adopt?**: YES
- **Why?**: Zero integration effort (just copy markdown), MIT license, provides immediate design direction for AI agents building aiZee UI. Use as reference or adopt specific DESIGN.md files that match desired aesthetic.
- **Effort**: small
- **Target component**: docs/, DESIGN.md (root)

---

## 7. Observability / SRE

### open-telemetry/opentelemetry-python
- **Category**: Observability / SRE
- **Summary**: CNCF-standard OpenTelemetry implementation for Python with API/SDK separation. Monorepo architecture with modular exporters (OTLP, Prometheus, Zipkin), propagators (B3, Jaeger), and instrumentation packages. Supports traces (stable), metrics (stable), and logs (development). Python 3.10+ with Apache-2.0 license.
- **Top takeaways**:
  - API/SDK split pattern: libraries depend only on `opentelemetry-api`, applications use `opentelemetry-sdk` - zero runtime overhead when disabled
  - SpanProcessor interface for hooks (on_start, on_end) with SynchronousMultiSpanProcessor and ConcurrentMultiSpanProcessor implementations
  - Context propagation via W3C TraceContext and baggage propagators with pluggable context runtime
  - Exporter abstraction with OTLP (gRPC/HTTP), Prometheus, Zipkin backends - switch backends without code changes
  - Semantic conventions package for standardized attribute naming across services
- **Adopt?**: YES
- **Why?**: Industry standard for distributed tracing, essential for aiZee observability. API/SDK separation enables library instrumentation without runtime cost. Active CNCF project with strong governance, stable traces/metrics signals, extensive framework integrations via contrib repo.
- **Effort**: medium
- **Target component**: runtime/telemetry/

### prometheus/client_python
- **Category**: Observability / SRE
- **Summary**: Official Prometheus Python client for metrics instrumentation. Registry-based collector pattern with Counter, Gauge, Histogram, Summary, Info metric types. Label-based time series with thread-safe child metric creation. Built-in collectors for process, GC, platform metrics. HTTP exposition endpoints for WSGI, ASGI, Django, Flask, aiohttp, Twisted. Python 3.9+ with Apache-2.0/BSD-2-Clause license.
- **Top takeaways**:
  - CollectorRegistry pattern with auto_describe for metric discovery, duplicate detection, and restricted_registry for filtering
  - Label-based metric hierarchy with lazy child creation via `.labels()` method, thread-safe with Lock
  - Multiprocess mode via `prometheus_multiproc_dir` for gunicorn/uWSGI worker aggregation
  - Context managers for exception counting, in-progress tracking, and timing decorators
  - OpenMetrics exposition format support with exemplars and native histograms
- **Adopt?**: YES
- **Why?**: De facto standard for metrics in Python ecosystems. Simple API, mature codebase, extensive framework integrations. Complements OpenTelemetry for pull-based metrics scraping. Low integration overhead with immediate value for runtime monitoring.
- **Effort**: small
- **Target component**: runtime/telemetry/

---

## 8. Ranked priority list

### Integrate first (YES)

Sorted by effort then fit. All have clear aiZee relevance and acceptable licenses.

#### Tier 1 — small effort, high impact

1. `poyao0705/guardian-angel` — purpose-built Python agent policy SDK; drop into `runtime/policies/`.
2. `VoltAgent/awesome-design-md` — zero-code design-token reference; seed `DESIGN.md` in root.
3. `dufangshi/orchestration-mcp` — MCP adapter pattern for backend-agnostic agent execution.
4. `fjb040911/ai-rules` — Markdown-to-Rule-IR compiler; upgrades `rules/` pipeline.
5. `prometheus/client_python` — metrics registry; complement OpenTelemetry in `runtime/telemetry/`.
6. `PlateerLab/synaptic-memory` — deterministic graph memory with MCP tools; fits `memory/` / `graphify-out/`.

#### Tier 2 — medium effort, high impact

7. `nizos/probity` — runtime guardrail with per-agent adapters; harden `runtime/kernel.py`.
8. `lastmile-ai/mcp-agent` — composable MCP orchestration patterns.
9. `mrorigo/mcp-orchestrator` — Code Mode execution; evaluate `runtime/codemode/`.
10. `shackleai/orchestrator` — org-chart governance + budgets for `rules/` and `aios_mcp/`.
11. `Justin0504/Sovereign-OS` — Charter-driven configuration and TrustScore gating.
12. `preloop/preloop` — control-plane (MCP firewall, model gateway, approvals).
13. `microsoft/agent-governance-toolkit` — enterprise policy/trust layer; mature compliance.
14. `facebook/astryx` — React 19 design system for `dashboard/` / `frontend/`.
15. `open-telemetry/opentelemetry-python` — standard tracing for `runtime/telemetry/`.

### Watch (HOLD)

Monitor for maturity or extract patterns only.

- `RightNow-AI/openfang` — study Hands pattern / WASM sandbox, but Rust stack is a mismatch.
- `nanny-run/nanny` — hard-limit primitives; borrow into policy design.
- `ViktorWelbers/paddock` — hierarchical budget ledger and gateway proxy patterns.
- `musaceylan/OrchestrAI` — multi-model routing, early stage.
- `open-policy-agent/opa` — Rego/bundles for infrastructure policies, not agent runtime.
- `MAIF/arta` — simple Python rule engine for ML/business rules reference.
- `neo4j-labs/agent-memory` — graph-native memory if Neo4j becomes acceptable.
- `MemMachine/MemMachine` — multi-framework memory abstraction.
- `mtrnix/metronix-memory` — hybrid retrieval and freshness pipeline.
- `yunbow/ai-dev-os` — 4-layer rule taxonomy for rule-organization inspiration.
- `stawils/coding-guardrails` — rule protocol and lint gates for local-LLM scenarios.

### Skip (NO / not found)

Not a fit or unavailable.

- `mnemopay/praetor` — repository not found.
- `chrisnewell91/Meta-MCP-Server` — process-heavy meta server; duplicate of orchestration concerns.
- `JonSil89/gatehouse-policy-engine` — DevOps change-management domain.
- `SemClone/ospac` — license-compliance dataset with non-commercial restriction.
- `XMUDeepLIT/MemGraphRAG` — research codebase, not production-ready.
- `xianzuyang9-blip/agent-guardrails` — empty placeholder repo.

## 9. Architect's opinion and integration playbook

### Overall assessment

The 32-repo scan reveals a maturing agent-OS market with strong convergence around four concerns: runtime governance, MCP orchestration, memory/RAG, and observability. aiZee already owns the runtime/policy skeleton (`runtime/kernel.py`, budget, policy engine). The **YES** repos fill the exact gaps: declarative tool governance, design tokens, MCP adapters, rule compilation, telemetry, and memory. They also confirm that a Python-first, FastAPI/MCP/TypeScript-adjacent stack is the correct long-term bet.

The **HOLD** list is valuable as pattern insurance: extract ideas without taking dependencies. The **SKIP** list validates our direction by showing what *not* to build or depend on.

### How to benefit

1. **Do not adopt whole frameworks**. Isolate each pattern as a module to preserve sovereignty and avoid lock-in.
2. **Prioritize small-effort, high-fit YES items first** to validate value before larger integrations.
3. **Mine HOLD repos for patterns only**: budget ledgers, rule taxonomies, freshness pipelines, sandbox primitives. Reimplement in our stack.
4. **Adoption gate for every integration**: MIT/Apache-2.0 license, no mandatory external SaaS, Python-first or clean API, matches `runtime/kernel.py` gate model.
5. **Layer defenses**: combine `guardian-angel` policy signals with `probity` runtime guardrails for defense-in-depth.

### Feature importance map

| Feature | Source repo | Why it matters for aiZee | Target component |
|---|---|---|---|
| Approval-required policy signal | `guardian-angel` | Closes the tool-call gate; enables human-in-the-loop and async approvals. | `runtime/policies/` |
| `DESIGN.md` token contract | `awesome-design-md` | Gives agents a zero-code design language, reducing UI drift. | root `DESIGN.md` / `dashboard/` |
| MCP adapter pattern | `orchestration-mcp` | Decouples MCP surface from execution backend; swap agent runtimes without rewrites. | `aios_mcp/adapters/` |
| Markdown-to-Rule-IR compiler | `ai-rules` | Turns Markdown rules into machine-checkable artifacts and audit prompts. | `rules/` |
| Prometheus metrics registry | `client_python` | Operational SRE metrics without external SaaS dependency. | `runtime/telemetry/` |
| Deterministic graph extraction | `synaptic-memory` | Builds memory/RAG with **zero LLM indexing cost** and no Neo4j lock-in. | `memory/`, `graphify-out/` |
| Composable agent patterns | `mcp-agent` | Reusable orchestration primitives (map-reduce, router, evaluator-optimizer). | `runtime/orchestrator/` |
| Code Mode execution | `mcp-orchestrator` | Cuts token burn 60-75% for multi-step workflows by emitting TypeScript instead of tool calls. | `runtime/codemode/` |
| Charter + TrustScore | `Sovereign-OS` | Declarative governance, zero standing privilege, JIT leases. | `runtime/`, `rules/` |
| MCP firewall + model gateway | `preloop` | Onboard existing agents (Claude Code, Cursor) through an enforced control plane. | `aios_mcp/`, `runtime/` |
| AgentMesh trust layer | `agent-governance-toolkit` | Enterprise identity, Ed25519, 5-dimension trust scoring, compliance mapping. | `rules/`, `runtime/` |
| Org-chart multi-agent governance | `shackleai/orchestrator` | Budget + role hierarchy for agent collectives. | `rules/`, `aios_mcp/` |
| React 19 design system | `astryx` | Production UI components with zero styling lock-in. | `dashboard/`, `frontend/` |
| OpenTelemetry tracing | `opentelemetry-python` | Industry-standard distributed observability. | `runtime/telemetry/` |
| Runtime file/shell guardrail | `probity` | Intercepts destructive writes and shell commands before execution. | `runtime/kernel.py` |

### Patterns to extract from HOLD repos

| Pattern | Source repo | Why it matters |
|---|---|---|
| Manifest-driven "Hands" | `openfang` | Packaged agent capabilities with `HAND.toml` + `SKILL.md` + guardrails. |
| Process-level hard limits | `nanny` | Fallback enforcement when in-process gates are bypassed. |
| Hierarchical budget ledger | `paddock` | Org → team → user → session budget inheritance. |
| Bundle-based policy distribution | `opa` | Rego bundles for infrastructure or advanced policy delivery. |
| POLE+O graph model | `agent-memory` | Graph-native memory for entity resolution. |
| Freshness pipeline | `metronix-memory` | Detect and reconcile stale/conflicting memory. |
| 4-layer rule taxonomy | `ai-dev-os` | Separate principles, criteria, guidelines, tool configs. |
| Rule protocol (allow/block/nudge) | `coding-guardrails` | Composable action resolution for guardrails. |

### 90-day integration plan

- **Weeks 1–2**: `guardian-angel` policy signals and `probity` guardrail patterns into `runtime/kernel.py`.
- **Weeks 3–4**: Seed a root `DESIGN.md` from `awesome-design-md`; evaluate `astryx` for `dashboard/`.
- **Month 2**: Build `aios_mcp/adapters/` using `orchestration-mcp`; prototype `ai-rules` Rule-IR compiler; wire `prometheus/client_python`.
- **Month 3**: Integrate `synaptic-memory` for deterministic graph memory; adopt `mcp-agent` patterns; design Charter/TrustScore model from `Sovereign-OS`.

### Risks to avoid

- Do not make Neo4j or Kubernetes a hard dependency.
- Do not pull in non-commercial datasets (`ospac`) or research-only code (`MemGraphRAG`).
- Do not build around early-stage projects (`OrchestrAI`, `agent-guardrails`) until they stabilize.
- Keep telemetry optional (API/SDK split like OpenTelemetry) so the OS can run fully offline.

### Summary

- **Adopt**: 15 of 31 cloned repos.
- **Watch**: 11 repos for patterns or future maturity.
- **Skip**: 5 repos plus 1 not found.
- Highest-value, lowest-risk starts: guardian-angel, awesome-design-md, orchestration-mcp, ai-rules, prometheus-client, synaptic-memory.

Temp directory `temp/repos-study/` retained per user request until task is complete.
