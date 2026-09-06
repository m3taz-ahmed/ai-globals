[TECH] OpenAI API 2026
[OBJ] OpenAI API 2026. GPT-6 Astra (frontier), GPT-5.6 Sol/Terra/Luna, GPT-Image-2, GPT-Realtime-2.1. Async tool calling, unified Responses API. Older gpt-5/o3 snapshots deprecated, shutdown 11 Dec 2026.
[RULES]
1. [REQ] Use unified Responses API (`client.responses.create`) for all text/image/audio workflows — replaces Chat Completions for new code. Chat Completions still supported but deprecated for new features.
2. [REQ] Use `gpt-6-astra` for frontier reasoning/coding tasks. Use `gpt-5.6-sol` for balanced cost/perf, `gpt-5.6-terra` for high-throughput, `gpt-5.6-luna` for low-latency edge.
3. [REQ] Use `gpt-image-2` for image generation: `client.images.generate` with `model="gpt-image-2"`. Supports edit, variation, inpainting.
4. [REQ] Use `gpt-realtime-2.1` for voice/audio: `client.realtime` WebSocket sessions. Low-latency streaming audio in/out.
5. [REQ] Use async tool calling: tools return promises/futures, API waits for resolution. `tools: [{type: "function", ...}]` with async handler — no manual polling.
6. [REQ] Use `tiktoken` for token counting before API calls: `tiktoken.encoding_for_model("gpt-6-astra").encode(text)`. Estimate cost + truncate context.
7. [REQ] Use Batch API (`client.batches.create`) for async workloads — 50% cost savings, 24-hour window, up to 50K requests per batch. Use for non-latency-sensitive bulk processing.
8. [REQ] Use structured outputs: `response_format: {"type": "json_schema", "json_schema": {...}}` with strict JSON schema. Guarantees schema compliance.
9. [REQ] Use streaming (`stream: true`) for UX responsiveness. Parse SSE events: `response.output_text.delta`, `response.completed`.
10. [REQ] Use function calling with `tools` + `tool_choice`. Handle `tool_calls` in response, return `tool_result` in next turn. Async tool calling eliminates manual orchestration.
11. [REQ] Use prompt caching: prefix-stable system prompts auto-cached (up to 90% cost reduction). Keep system prompt + tool definitions stable across requests.
12. [REQ] Use `temperature` (0-2) + `top_p` for sampling control. `temperature: 0` for deterministic, `0.7` for balanced, `1.0+` for creative.
13. [REQ] Use `max_output_tokens` (not `max_tokens` in Responses API) to cap response length.
14. [REQ] Migrate from deprecated `gpt-5` / `o3` snapshots before 11 Dec 2026 shutdown. Use `gpt-5.6-*` or `gpt-6-astra` replacements.
15. [REQ] Use `OPENAI_API_KEY` env var or secrets manager. Never hardcode keys.
16. [CMD] `pip install openai tiktoken` install Python SDK + tokenizer.
17. [CMD] `npm install openai` install Node SDK.
18. [CMD] `client.responses.create(model="gpt-6-astra", input="...")` basic call.
19. [PROHIBIT] Never use deprecated `gpt-5` / `o3` snapshots after 11 Dec 2026 — will return errors.
20. [PROHIBIT] Never hardcode API keys in source/client code — use backend proxy.
21. [PROHIBIT] Never use `max_tokens` with Responses API — use `max_output_tokens`.
22. [PROHIBIT] Never send PII/credentials in prompts without data processing agreement.
[COMPAT]
- OpenAI API 2026 (Responses API unified).
- Models: gpt-6-astra, gpt-5.6-sol/terra/luna, gpt-image-2, gpt-realtime-2.1.
- Deprecated: gpt-5 snapshots, o3 snapshots (shutdown 11 Dec 2026).
- SDK: openai-python 1.50+, openai-node 5.0+.
- tiktoken 0.8+ for token counting.
[REFS]
- https://platform.openai.com/docs/api-reference/responses
- https://platform.openai.com/docs/guides/structured-outputs
- https://platform.openai.com/docs/guides/batch
- https://github.com/openai/tiktoken
