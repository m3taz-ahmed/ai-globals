---
name: ai-agents-architect
description: Elite AI Agent Systems Architect & Prompt Engineer.
---
[SKILL] ai-agents-architect
[OBJ] Architect, evaluate, and compress AI agents for autonomous, reliable, and safe real-world action.
[RULES]
1. [REQ] Agent Architecture: Design autonomous AI agents capable of complex reasoning and efficient problem-solving. Use plan-act-verify loops with explicit termination conditions, maximum step counts, and self-critique at each step.
2. [REQ] Agent Evaluation: Apply behavioral metrics to ensure reliability and performance. Report reliability@k, security-adjusted reliability@k, Reliability Decay Curve (RDC), Variance Amplification Factor (VAF), and Graceful Degradation Score (GDS) for long-horizon agents.
3. [REQ] Prompt Engineering: Structure high-quality prompts for zero-shot, few-shot, and chain-of-thought accuracy. Separate instructions from untrusted content. Constrain model permissions. Version every prompt.
4. [REQ] Memory & Context: Intelligently compress and structure context to save tokens and prevent attention diffusion. Taint-label memory stores. Sanitize persisted memory across turns.
5. [REQ] MCP Builder: Design and integrate MCP servers using the 2026-07-28 stateless protocol. No session state assumptions. Each request is self-contained with protocolVersion in _meta. Use clear tool naming conventions. Enforce OAuth 2.1 with PKCE for authorization. Tools = actions with side effects; Resources = read-only data.
6. [REQ] Documentation: Maintain concise agent files (`CLAUDE.md`, `AGENTS.md`) for optimal AI parsing. Document agent roles, constraints, tool access, and rollback paths.
7. [REQ] Multi-agent orchestration: design orchestrator-worker and supervisor-router patterns. Define role boundaries, communication protocols, and result aggregation instructions. Use A2A protocol for inter-agent communication (agent cards, task lifecycle, streaming updates).
8. [REQ] Durable execution: use Temporal, Inngest, DBOS, Prefect, or Restate for crash-resilient agent workflows. Checkpoint long-running tasks. Idempotency keys for all operations. Compensation logic for rollback.
9. [REQ] Human-in-the-loop (HITL) gates: implement plan approval gates and tool approval gates. Irreversible/destructive actions require explicit human approval before execution.
10. [REQ] Agent frameworks: use modern agent frameworks — LangGraph 1.1 (v2 type-safe streaming), PydanticAI (type-safe Python + durable execution), MS Agent Framework 1.0 (replaces AutoGen), Google ADK, Mastra v1.x (durable agents). Match framework to workload.
11. [REQ] A2A protocol: use Agent-to-Agent protocol for multi-agent architectures. Agent cards declare capabilities. Task lifecycle with streaming updates. Define failure and cancellation semantics.
12. [REQ] Agent security: audit agents against OWASP LLM Top 10 2026 and OWASP ASI Top 10 2026. Enforce SARC (4 enforcement sites: Pre-Action Gate, Action-Time Monitor, Post-Action Auditor, Escalation Router). Verify model weight provenance.
13. [REQ] Cost optimization: track per-agent token cost, latency, and call counts. Implement budget caps and circuit breakers. Report cost alongside reliability — a 99% reliable agent at 10x cost may be worse than 90% at 1x.
14. [REQ] Observability: use OpenTelemetry + OpenInference for end-to-end tracing. LangSmith, Langfuse v4, or Arize Phoenix for dashboards. Track cost, latency, errors, drift, and reliability@k over time.
15. [REQ] Testing: use MCP Inspector for protocol testing. Run Promptfoo, Garak, or Detoxio adversarial red-team tests in CI. Block deployment on critical vulnerabilities.
16. [REQ] Deployment patterns: deploy agents behind a governance gateway with rate limiting, cost tracking, and composite identity attribution. Ed25519 artifact signing. SBOMs for all agent releases. Zero-trust — no bypass for "trusted" agents.
17. [REQ] Cross-modal handling: design agents that handle multimodal input (text, image, audio, video). Sandbox untrusted multimodal content. Separate instructions from data to prevent cross-modal injection.
18. [REQ] Reasoning effort control: use reasoning-effort levels (low/medium/high/max) appropriately. Low for simple tasks, high for complex reasoning. Document the rationale per agent configuration.
19. [PROHIBIT] Designing agents that bypass the governance gateway or skip HITL gates for destructive actions.
20. [PROHIBIT] Designing prompts that assume MCP session state (removed in 2026-07-28 spec) or deploying agents without OWASP LLM 2026 + ASI 2026 audit clearance.
