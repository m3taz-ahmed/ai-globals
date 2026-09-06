# Workflow 56 — Agent SRE Governance

[TRIGGER] agent sre, agent slo, agent error budget, agent circuit breaker, agent observability, sre governance
[PERSONA] SRE, ARCH, SEC, DEVOPS
[TECH] opentelemetry-2026

## Objective

Implement Agent SRE Governance v1.0 (Microsoft Agent Governance Toolkit pattern) for all AI coding agent deployments. SLOs, error budgets, circuit breakers, chaos engineering, trace replay, Ed25519 artifact signing, SBOMs, and OpenTelemetry tracing.

## Steps

1. **Define agent SLOs.** For each agent in `runtime/agent_catalog.py`, define: success rate target (e.g., 99.5%), latency p99 target (e.g., 30s), cost per task target (e.g., $0.50), reliability@k target (e.g., 0.90 at k=5).

2. **Define error budgets.** Error budget = 1 - SLO target. For 99.5% success rate, error budget = 0.5% per period (e.g., monthly). Track budget consumption. When budget exhausted, freeze new agent deployments and focus on reliability.

3. **Implement circuit breakers.** In `runtime/agent_gateway.py`, add circuit breakers for: cost velocity (spend > threshold per minute), repeated prompts (same prompt > N times per minute), error rate (errors > threshold per minute), context growth (context size > threshold). Circuit open = BLOCK + cooldown.

4. **Chaos engineering for agents.** Inject failures: LLM timeout, LLM 500 error, MCP tool timeout, MCP tool error, network partition, disk full. Verify agent degrades gracefully. Run in staging weekly.

5. **Trace replay.** Store golden traces (successful agent executions). Replay against new agent versions. Regression = trace divergence > threshold. Use OpenTelemetry trace replay.

6. **Ed25519 artifact signing.** Sign every agent artifact (generated code, plans, diffs) with Ed25519. Verify signature on pull. Unsigned artifact = BLOCK. Use `cryptography` library for signing.

7. **AI/ML SBOMs.** Generate SBOM for every agent deployment: model, framework, dependencies, serialization format. CycloneDX AI extension or SPDX 3.0 AI profile. `aizee sbom generate` before release.

8. **OpenTelemetry tracing.** Instrument all agent calls with OTel + OpenInference span attributes: `gen_ai.system`, `gen_ai.request.model`, `gen_ai.usage.prompt_tokens`, `gen_ai.usage.completion_tokens`, `gen_ai.tool.name`, `gen_ai.tool.call.result`, `gen_ai.guardrail.name`, `gen_ai.guardrail.verdict`. Export to Langfuse, Phoenix, or LangSmith.

9. **Per-agent, per-team budget enforcement.** Track cost per agent and per team. Enforce budgets via `runtime/cost_attribution.py`. Budget breach = alert + optional throttle. Per-PR spend caps (soft block) per Devin enterprise pattern.

10. **Golden-trace regression suite.** Maintain suite of golden traces for critical agent workflows. Run on every agent version change. Divergence > threshold = BLOCK deployment.

11. **SARC 4-site enforcement.** Verify all 4 enforcement sites active: Pre-Action Gate (block injection/PII/policy), Action-Time Monitor (rate/cost/budget), Post-Action Auditor (log/evaluate/score), Escalation Router (human approval/kill-switch/incident).

12. **Microsoft Agent Hooks.** Support framework-neutral governance contracts — "deny means deny" enforceable across LangChain, CrewAI, OpenAI Agents SDK. Integrate with `runtime/agent_gateway.py`.

13. **5-layer control plane.** Verify all 5 layers active: Gateway (auth/rate/cost), Policy (4-level hierarchy/fail-closed), Observability (tamper-evident audit), Governance (approvals/kill-switch/RBAC), Integration (A2A/MCP/REST/webhooks).

14. **Dashboard.** Display SLO status, error budget consumption, circuit breaker state, cost attribution, reliability@k scores. Use existing dashboard or integrate with Grafana.

15. **Quality gate.** Run `ruff check .`, `mypy`, `aizee test --full`, `python eval/harness.py`. Verify all agents have SLOs, error budgets, circuit breakers, OTel tracing, Ed25519 signing.

16. **Memory sync.** Update `Memory.md` with Agent SRE Governance milestone. Update `CHANGELOG.md` `[Unreleased]` section.

## References

- `skills/agent-governance-lord/SKILL.md` — Agent governance lord
- `skills/ai-observability-lord/SKILL.md` — AI observability lord
- `tech-stack/opentelemetry-2026.md` — OpenTelemetry + OpenInference
- https://microsoft.github.io/agent-governance-toolkit/specs/AGENT-SRE-GOVERNANCE-1.0/
- https://arxiv.org/html/2606.15954 — SARC
