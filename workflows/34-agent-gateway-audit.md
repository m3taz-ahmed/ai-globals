---
name: 34-agent-gateway-audit
trigger: agent gateway, runtime audit, gateway audit, traffic audit, بوابة الوكلاء
engine: runtime/agent_gateway.py
---

# Workflow 34 — Agent Gateway Audit

[OBJ] Audit all LLM/MCP traffic passing through the agent gateway. Every request and response inspected, verdicted, and logged.

## Problem

A policy written in a document is not enforcement. Controls only hold where they sit on the agent's request and response path. IDE settings are advisory. CI scans are post-hoc. The gateway is the one place policy becomes enforceable.

## Phases

### Phase 1 — Register guardrails
1. Built-in guardrails auto-registered: `secret_leak` (pre-LLM), `prompt_injection` (post-execution), `destructive_command` (post-execution).
2. Register custom guardrails via `AgentGateway.register(name, phase, fn)`.
3. List active guardrails: `gateway.list_guardrails()`.

### Phase 2 — Intercept requests (pre-LLM)
1. Every outbound prompt + tool payload → `gateway.check_request(ctx)`.
2. Pre-LLM guardrails inspect: secret leakage in prompt, forbidden tool calls, prompt injection in tool responses fed back.
3. Verdict: ALLOW / REDACT / BLOCK. Most severe wins.
4. BLOCK → request never reaches the LLM. Log + alert.
5. REDACT → secrets stripped, request proceeds. Log redacted fields.

### Phase 3 — Intercept responses (post-execution)
1. Every inbound response + generated code → `gateway.check_response(ctx)`.
2. Post-execution guardrails inspect: destructive commands, insecure patterns, hallucinated APIs, prompt injection in tool output.
3. Verdict: ALLOW / REDACT / BLOCK.
4. BLOCK → response never reaches the developer. Log + alert.

### Phase 4 — Composite identity attribution
1. Every verdict logged with `agent_id` + `user_id` from `GuardrailContext`.
2. Cross-reference with `runtime/composite_identity.py` for full dual-principal attribution.
3. No anonymous agent actions.

### Phase 5 — Audit + report
1. `gateway.verdict_log(limit=50)` → recent verdicts.
2. Export to audit trail via `AuditLogger.log("gateway_verdict", {...})`.
3. Report: total requests, total responses, BLOCK count, REDACT count, top blocking guardrails.

## Commands (PowerShell)

```powershell
# Inspect verdict log
python -c "from runtime.agent_gateway import AgentGateway; g = AgentGateway(); print(g.verdict_log(50))"

# List guardrails
python -c "from runtime.agent_gateway import AgentGateway; g = AgentGateway(); print(g.list_guardrails())"
```

## Quality Gate

- All requests pass through gateway (no bypass).
- Every verdict logged with composite identity.
- `ruff check runtime/agent_gateway.py` PASS.
- `pytest tests/test_agent_gateway.py -q` PASS.
