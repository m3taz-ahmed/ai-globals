---
name: prompt-engineer
description: LLM prompt engineering covering system design, few-shot, chain-of-thought, structured output, and evaluation
---
[SKILL] prompt-engineer
[OBJ] Design, version, evaluate, and harden LLM prompts that produce reliable, structured, and safe outputs across deployments.
[RULES]
1. [REQ] Design a clear system prompt that defines the model role, task scope, output format, tone, and explicit constraints.
2. [REQ] Include few-shot examples that cover representative cases including edge cases and expected refusals.
3. [REQ] Use chain-of-thought prompting for reasoning tasks; instruct the model to expose intermediate steps before the final answer.
4. [REQ] Request structured output via JSON mode or a strict schema definition; validate responses against the schema programmatically.
5. [REQ] Tune temperature and sampling parameters deliberately: low temperature for deterministic tasks, higher for creative, and document the rationale.
6. [REQ] Manage the context window: prioritize recent and relevant context, summarize long history, and stay within token limits with headroom.
7. [REQ] Defend against prompt injection: separate instructions from user data, sanitize untrusted input, and constrain model permissions.
8. [REQ] Define evaluation metrics (accuracy, faithfulness, format compliance, latency, cost) and run them on every prompt change.
9. [CMD] A/B test candidate prompts against the current production prompt using the same evaluation set and statistical comparison.
10. [CMD] Version every prompt with an identifier and changelog; record the model, parameters, and evaluation scores per version.
11. [PROHIBIT] Hardcoding prompts in application code without versioning and a retrieval mechanism.
12. [PROHIBIT] Promoting a prompt to production without running the evaluation suite and comparing against the baseline.
