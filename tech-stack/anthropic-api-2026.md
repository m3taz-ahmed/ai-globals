[TECH] Anthropic API 2026
[OBJ] Anthropic API 2026. Claude Fable 5.1 (Sep 2026), Claude Opus 5 (Jul 2026). 1M token context, 128k output, always-on adaptive thinking, mid-conversation tool changes, automatic fallbacks, Enterprise Frontier Safeguards. Fast mode removed for Opus 4.7.
[RULES]
1. [REQ] Use `claude-fable-5-1` (latest, Sep 2026) for frontier reasoning/coding. Use `claude-opus-5` (Jul 2026) for high-intelligence tasks. Check model availability per tier.
2. [REQ] Use Messages API (`client.messages.create`) with `model`, `max_tokens`, `messages`. `system` is top-level param, not in `messages` array.
3. [REQ] Use 1M token context: `max_tokens` up to 128K output. Verify tier access for 1M context (enterprise/usage thresholds).
4. [REQ] Use always-on adaptive thinking: model auto-decides thinking budget based on task complexity. No manual `thinking` config needed (but can override with `thinking={"type": "enabled", "budget_tokens": N}`).
5. [REQ] Use mid-conversation tool changes: add/remove/modify tools between turns without restarting conversation. `tools` array can differ per request.
6. [REQ] Use automatic fallbacks: configure `fallback_models` in request — API auto-downgrades if primary model overloaded/unavailable. `model: "claude-fable-5-1", fallback_models: ["claude-opus-5"]`.
7. [REQ] Use Enterprise Frontier Safeguards: enhanced safety filters for enterprise deployments. Enable via account settings or `safety_level: "enterprise"` param.
8. [REQ] Use prompt caching: `cache_control: {"type": "ephemeral"}` on system/tools/large context. 90% cost reduction for repeated prefixes. 5-minute TTL (extendable).
9. [REQ] Use tool use: `tools` with `input_schema` (JSON schema). Handle `tool_use` blocks, return `tool_result` in next user message.
10. [REQ] Use structured output via tool use: define a single tool with desired schema, force `tool_choice: {"type": "tool", "name": "extract"}`. Parse `tool_use.input`.
11. [REQ] Use Message Batches API (`client.messages.batches.create`) for async: up to 100K requests, 24-hour window, 50% cost savings.
12. [REQ] Use streaming (`stream: true`) with SSE: `message_start`, `content_block_delta`, `message_stop`. Parse `delta.text` / `delta.partial_json`.
13. [REQ] Use vision: image content blocks `{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": "..."}}`.
14. [REQ] Use `anthropic` Python SDK (>=0.40) or `@anthropic-ai/sdk` Node SDK (>=0.35). Auto-reads `ANTHROPIC_API_KEY`.
15. [REQ] Migrate from `claude-opus-4-7` Fast mode — removed in 2026. Use standard mode or `claude-opus-5`.
16. [CMD] `pip install anthropic` install Python SDK.
17. [CMD] `npm install @anthropic-ai/sdk` install Node SDK.
18. [CMD] `export ANTHROPIC_API_KEY="sk-ant-..."` set API key.
19. [PROHIBIT] Never use Fast mode for `claude-opus-4-7` — removed. Migrate to `claude-opus-5`.
20. [PROHIBIT] Never hardcode API keys in client-side code — use backend proxy.
21. [PROHIBIT] Never exceed `max_tokens` beyond model output limit (128K for Fable 5.1 / Opus 5).
22. [PROHIBIT] Never include PII/credentials in prompts without data processing agreement.
[COMPAT]
- Anthropic API 2026.
- Models: claude-fable-5-1 (Sep 2026), claude-opus-5 (Jul 2026).
- Context: 1M tokens input, 128K tokens output.
- Breaking: Fast mode removed for Claude Opus 4.7.
- SDK: anthropic-python 0.40+, @anthropic-ai/sdk 0.35+.
- Enterprise Frontier Safeguards available.
[REFS]
- https://docs.anthropic.com/en/api/messages
- https://docs.anthropic.com/en/docs/build-with-claude/tool-use
- https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching
- https://docs.anthropic.com/en/docs/build-with-claude/batch-processing
