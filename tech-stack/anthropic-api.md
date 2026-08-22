[TECH] Anthropic API
[OBJ] Cloud API for Claude 3.5 Sonnet and Haiku models via the Messages API with tool use, prompt caching, extended thinking, and batch processing.
[RULES]
1. [REQ] Use the official `anthropic` Python SDK (>=0.39.0) or `@anthropic-ai/sdk` npm package; construct the client with `Anthropic()` which auto-reads `ANTHROPIC_API_KEY`.
2. [REQ] Load the API key from `ANTHROPIC_API_KEY` environment variable or a secrets manager; never hardcode keys in source or configuration files.
3. [REQ] Use the Messages API (`client.messages.create`) with `model`, `max_tokens`, and `messages` (a list of `{"role": "user"|"assistant", "content": ...}` dicts); the `system` parameter is top-level, not inside `messages`.
4. [REQ] Always specify `max_tokens` (required parameter); set it to the minimum sufficient value to control cost and latency.
5. [REQ] Use `claude-3-5-sonnet-20241022` for complex reasoning and coding tasks; use `claude-3-5-haiku-20241022` for high-throughput, low-latency workloads.
6. [REQ] For tool use, define `tools` with JSON schema `input_schema`; handle `tool_use` content blocks in the response and return `tool_result` blocks in the next user message.
7. [REQ] Enable prompt caching by setting `cache_control: {"type": "ephemeral"}` on system prompts or large context blocks; this reduces latency and cost for repeated prefixes by up to 90%.
8. [REQ] Use extended thinking (`thinking={"type": "enabled", "budget_tokens": N}`) with Claude 3.5 Sonnet for multi-step reasoning; reserve a sufficient `max_tokens` budget above `budget_tokens`.
9. [REQ] Implement retry logic for 429 (rate_limit_error) and 529 (overloaded_error) responses with exponential backoff; the SDK supports `max_retries` on the client.
10. [REQ] Use the Message Batches API (`client.messages.batches.create`) for asynchronous workloads up to 100,000 requests with a 24-hour window; poll `client.messages.batches.retrieve()` for status.
11. [REQ] For vision/multimodal, pass image content blocks as `{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": "..."}}` within the `content` array.
12. [CMD] `pip install anthropic` to install the Python SDK.
13. [CMD] `export ANTHROPIC_API_KEY="sk-ant-..."` to set the API key.
14. [PROHIBIT] Never pass `max_tokens` greater than the model's output limit (8192 for Claude 3.5 Sonnet/Haiku); the API will reject the request.
15. [PROHIBIT] Never include API keys in client-side code, browser bundles, or mobile apps; all calls must route through a backend proxy.
[COMPAT]
- Python SDK: anthropic>=0.39.0 (Python 3.8+)
- Node SDK: @anthropic-ai/sdk>=0.32.0 (Node 18+)
- Models: claude-3-5-sonnet-20241022, claude-3-5-haiku-20241022, claude-3-opus-20240229
[REFS]
- https://docs.anthropic.com/en/api/messages
- https://docs.anthropic.com/en/docs/build-with-claude/tool-use
- https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching
- https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking
