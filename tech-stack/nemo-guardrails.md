[TECH] NeMo Guardrails v0.24
[OBJ] NVIDIA NeMo Guardrails v0.24. Five rail types (input, dialog, retrieval, execution, output), Colang DSL, IORails for OpenAI-style tool calls, Polygraf PII integration, HF classifiers, context-bloat rail. Repo: NVIDIA-NeMo/Guardrails.
[RULES]
1. [REQ] Use five rail types: `input rails` (validate user input), `dialog rails` (control conversation flow), `retrieval rails` (filter RAG context), `execution rails` (wrap tool/LLM calls), `output rails` (validate model output).
2. [REQ] Use Colang DSL for rail definitions: `define user ask about X "..."` + `define bot respond Y`. Natural-language flow definitions compiled to executable rails.
3. [REQ] Use IORails for OpenAI-style tool calls: intercept + validate tool call inputs/outputs. `define flow tool_call_guard: execute tool_call_guardrails`.
4. [REQ] Use Polygraf PII integration: detect + redact PII (SSN, email, phone, credit card) in input/output. `input rails: { pii: { enabled: true, provider: "polygraf" } }`.
5. [REQ] Use HuggingFace classifiers for content moderation: `model: "facebook/roberta-hate-speech-dynabench-r4-target"`. Configure per-rail in `config.yml`.
6. [REQ] Use context-bloat rail: limit context window size to prevent token overflow + cost. `define flow context_bloat_guard: execute truncate_context max_tokens=4000`.
7. [REQ] Use `nemoguardrails` Python package: `from nemoguardrails import RailsConfig, LLMRails`. `config = RailsConfig.from_path("./config")`, `rails = LLMRails(config)`.
8. [REQ] Use `rails.generate(messages=[{"role": "user", "content": "..."}])` for guarded generation. Rails auto-apply input → dialog → retrieval → execution → output.
9. [REQ] Use `config.yml` for config: models, rails, embeddings, instructions. `config/` dir with `config.yml`, `flows.co`, `actions.py`.
10. [REQ] Use custom actions: `from nemoguardrails import actions`. `@actions.action(is_system_action=True) async def my_action(context): ...`. Call from Colang flows.
11. [REQ] Use `output rails` to prevent jailbreaks/leaks: `define flow check_output: execute check_output_toxicity`. Block responses containing sensitive content.
12. [REQ] Use `input rails` to block prompt injection: `define flow check_input: execute check_injection`. Detect "ignore previous instructions" patterns.
13. [REQ] Use `retrieval rails` for RAG: filter retrieved chunks by relevance + safety. `define flow retrieval_guard: execute filter_retrieved_context`.
14. [REQ] Use `execution rails` to wrap LLM calls: pre/post hooks on `rails.generate`. Log, rate-limit, validate before/after model call.
15. [REQ] Use evaluation: `nemoguardrails eval` runs test cases against rails config. `eval/` dir with test scenarios.
16. [CMD] `pip install nemoguardrails` install package.
17. [CMD] `nemoguardrails init` scaffold new project (config.yml, flows.co, actions.py).
18. [CMD] `nemoguardrails eval` run evaluation suite.
19. [PROHIBIT] Never deploy LLM apps without input + output rails in production.
20. [PROHIBIT] Never disable PII redaction for user-facing apps — compliance requirement (GDPR/CCPA).
21. [PROHIBIT] Never use Colang flows without testing — complex flows can deadlock or loop.
22. [PROHIBIT] Never skip eval suite before deploying new rails config.
[COMPAT]
- NeMo Guardrails v0.24 (NVIDIA).
- Repo: NVIDIA-NeMo/Guardrails.
- Models: OpenAI, Anthropic, Google, NVIDIA NIM, HuggingFace, Ollama.
- Polygraf PII integration.
- HuggingFace classifiers for moderation.
- Python 3.9+ (3.14 compatible).
[REFS]
- https://github.com/NVIDIA-NeMo/Guardrails
- https://docs.nvidia.com/nemo/guardrails/
- https://github.com/NVIDIA-NeMo/Guardrails/blob/main/docs/
- https://docs.nvidia.com/nemo/guardrails/user-guides/
