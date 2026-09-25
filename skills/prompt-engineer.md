---
name: prompt-engineer
description: LLM prompt engineering covering system design, few-shot, chain-of-thought, structured output, and evaluation
---
[SKILL] prompt-engineer
[OBJ] Design, version, evaluate, and harden LLM prompts that produce reliable, structured, and safe outputs across deployments.
[RULES]
1. [REQ] Design a clear system prompt that defines the model role, task scope, output format, tone, and explicit constraints.
2. [REQ] Include few-shot examples that cover representative cases including edge cases and expected refusals.
3. [REQ] Use chain-of-thought reasoning for complex tasks; prefer concise rationale, structured evidence, and verifiable outputs. Do NOT require the model to expose private hidden chain-of-thought — instead require structured intermediate results (e.g., step summaries, evidence citations, verification checks) that are testable and auditable.
4. [REQ] Request structured output via JSON mode or a strict schema definition; validate responses against the schema programmatically.
5. [REQ] Tune temperature and sampling parameters deliberately: low temperature for deterministic tasks, higher for creative, and document the rationale.
6. [REQ] Manage the context window: prioritize recent and relevant context, summarize long history, and stay within token limits with headroom.
7. [REQ] Defend against prompt injection: separate instructions from user data, sanitize untrusted input, and constrain model permissions.
8. [REQ] Define evaluation metrics (accuracy, faithfulness, format compliance, latency, cost) and run them on every prompt change.
9. [CMD] A/B test candidate prompts against the current production prompt using the same evaluation set and statistical comparison.
10. [CMD] Version every prompt with an identifier and changelog; record the model, parameters, and evaluation scores per version.
11. [PROHIBIT] Hardcoding prompts in application code without versioning and a retrieval mechanism.
12. [PROHIBIT] Promoting a prompt to production without running the evaluation suite and comparing against the baseline.
13. [REQ] MCP tool use prompting: design prompts that correctly invoke MCP tools. Include tool descriptions, parameter schemas, and error handling instructions. Tools are actions with side effects — prompt must constrain usage.
14. [REQ] Agentic prompting: design prompts for autonomous agents with plan-act-verify loops. Include termination conditions, maximum step counts, and self-critique instructions.
15. [REQ] Multi-agent orchestration prompting: design prompts for orchestrator and worker agents. Define role boundaries, communication protocols, and result aggregation instructions.
16. [REQ] MCP 2026-07-28 stateless prompting: design prompts for stateless MCP servers. No session state assumptions. Each request is self-contained with protocolVersion in _meta.
17. [REQ] Durable execution prompting: design prompts for long-running, crash-resilient workflows. Include checkpoint instructions, idempotency keys, and compensation logic.
18. [REQ] Cross-modal prompt design: design prompts that handle multimodal input (text, image, audio, video). Separate instructions from untrusted content. Sandbox multimodal data.
19. [REQ] Reasoning effort control: use reasoning-effort levels (low/medium/high/max) appropriately. Low for simple tasks, high for complex reasoning. Document the rationale per prompt.
20. [PROHIBIT] Designing prompts that assume MCP session state (removed in 2026-07-28 spec).
21. [REQ] Intent extraction before generation (prompt-master v1.8): silently extract 9 dimensions — task, target tool, output format, constraints, input, context, audience, success criteria, examples. Missing critical dimensions → max 3 targeted clarifying questions, then produce. Never ask >3.
22. [REQ] Model recency gate: when a prompt depends on a named model or "latest" behavior, verify model/controls against official provider docs (Context7/web). Never invent model slugs, context sizes, or parameter names. Same as [VER-01] for prompts.
23. [REQ] Risky single-pass techniques are opt-in only: Mixture-of-Experts simulation, Tree-of-Thought, Graph-of-Thought, self-consistency sampling, layered prompt chains carry fabrication risk in a single forward pass — apply ONLY on explicit user request when the target supports them.
24. [REQ] Token-efficiency audit: every word must be load-bearing. Strip adjectives, restatement, and filler that do not change the output. Deliver one copyable block + one-line strategy note.
25. [REQ] Zone structure for generated system prompts: PRIMACY zone (identity + hard NEVER rules + output lock) then MIDDLE zone (execution logic, tool routing, diagnostics) — primacy wins on conflict; keep rules in primacy minimal and absolute.
