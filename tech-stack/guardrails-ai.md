[TECH] Guardrails AI v0.10.2 (Jun 2026)
[OBJ] Composable LLM output validators — per-risk validators (toxicity, PII, profanity, hallucination, bias). Best for field-level / structured-output validation. Apache 2.0.
[RULES]
1. [REQ] Use Guardrails AI for field-level + structured-output validation — compose validators per risk: toxicity, PII, profanity, hallucination, bias.
2. [REQ] Define validators as composable units — `Guard().use(ToxicityValidator(), PIIValidator(), ProfanityValidator())`.
3. [REQ] Use `pydantic` models with `Field` validators for structured output schemas — Guardrails wraps Pydantic for LLM output parsing + validation.
4. [REQ] Use `Guard.parse()` / `Guard.validate()` to validate LLM output against schema + validators.
5. [REQ] Configure validator thresholds (e.g., toxicity score < 0.5) — fail validation if threshold exceeded.
6. [REQ] Use `on_fail` / `on_fail_repair` callbacks for validation failures — retry, reformat, or reject.
7. [REQ] Use field-level validators: annotate Pydantic fields with `Field(validators=[...])` for per-field validation.
8. [REQ] Use structured output validation for JSON/CSV/markdown outputs — parse + validate in one step.
9. [REQ] Integrate Guardrails in inference pipeline — validate before returning LLM output to user.
10. [REQ] Use `Guard.history` to track validation attempts + repairs for debugging.
11. [REQ] Apache 2.0 license — safe for commercial use.
12. [PROHIBIT] Never use Guardrails for full-response sentiment or open-ended text quality — use for field-level / structured validation.
13. [PROHIBIT] Never skip validation on "trusted" LLM outputs — always validate.
14. [PROHIBIT] Never use raw regex for PII detection — use Guardrails PII validator.
15. [PROHIBIT] Never silently swallow validation failures — log + handle via `on_fail` callback.
16. [CMD] `pip install guardrails-ai==0.10.2` — install.
17. [CMD] `guardrails hub install toxicity` — install hub validator.
18. [CMD] `guardrails configure` — configure validators.
19. [CMD] `guardrails validate` — CLI validate output.
20. [CMD] `guardrails parse` — CLI parse + validate.
[COMPAT]
- Guardrails AI v0.10.2 (Jun 2026).
- Python 3.10+.
- Pydantic v2 integration.
- Apache 2.0 license.
- Hub validators: toxicity, PII, profanity, hallucination, bias.
[REFS]
- https://www.guardrailsai.com/
- https://github.com/guardrails-ai/guardrails
- https://hub.guardrailsai.com/
