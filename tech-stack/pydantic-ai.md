[TECH] PydanticAI
[OBJ] PydanticAI — type-safe Python agent framework. Durable execution via Temporal/DBOS/Prefect/Restate, MCP support, streaming, structured output via Pydantic.
[RULES]
1. [REQ] Use `pydantic-ai` package: `from pydantic_ai import Agent`. Define agents with typed dependencies + result types: `Agent(model, deps_type=MyDeps, result_type=MyResult)`.
2. [REQ] Use structured output via Pydantic: `result_type=MyModel` — agent returns validated Pydantic model. SDK auto-generates JSON schema for the model and enforces it.
3. [REQ] Use durable execution via integrations: Temporal (`pydantic-ai-temporal`), DBOS (`dbos-pydantic-ai`), Prefect (`prefect-pydantic-ai`), Restate. Enables resume/replay after crashes.
4. [REQ] Use MCP support: `from pydantic_ai.mcp import MCPServerStdio, MCPServerSSE`. `agent = Agent(model, mcp_servers=[server])`. Tools/resources auto-discovered.
5. [REQ] Use streaming: `async with agent.run_stream(prompt) as result: async for chunk in result.stream(): ...`. Supports `stream_text`, `stream_structured`, `stream_responses`.
6. [REQ] Use typed dependencies: `deps_type=MyDeps` — inject DB clients, APIs, config via `RunContext[Deps]`. `async def tool(ctx: RunContext[MyDeps], query: str) -> ...`.
7. [REQ] Use function tools: `@agent.tool` decorator. Type hints auto-generate schema. `@agent.tool_plain` for tools without `RunContext` dependency.
8. [REQ] Use system prompts: `@agent.system_prompt` decorator (static or dynamic via `ctx`). `agent = Agent(model, system_prompt="...")` for static.
9. [REQ] Use `model` from `pydantic_ai.models`: `OpenAIModel("gpt-6-astra")`, `AnthropicModel("claude-fable-5-1")`, `GoogleModel("gemini-3.8-flash")`, `GroqModel(...)`.
10. [REQ] Use `FunctionModel` / `TestModel` for testing: `agent = Agent(TestModel(), result_type=MyResult)`. Deterministic, no API calls.
11. [REQ] Use `agent.run(prompt, deps=deps)` for sync, `await agent.run(...)` for async. Returns `AgentRunResult` with `.data` (typed result) + `.usage()` (tokens/cost).
12. [REQ] Use `usage_limits` to cap tokens/cost: `agent.run(prompt, usage_limits=UsageLimits(request_limit=10, total_tokens=10000))`.
13. [REQ] Use `agent.run_stream()` for streaming responses. Handle `result.validate()` for structured streaming.
14. [REQ] Use multi-agent handoffs: `agent = Agent(model, tools=[other_agent.as_tool(...)])`. Or explicit delegation via tool returning `Deps` for next agent.
15. [REQ] Use `pydantic-ai-slim` for minimal install (no provider packages) — install provider packages separately.
16. [CMD] `pip install pydantic-ai` install full package.
17. [CMD] `pip install pydantic-ai-slim pydantic-ai-openai pydantic-ai-anthropic` install slim + providers.
18. [CMD] `pip install pydantic-ai-temporal` install Temporal durable execution.
19. [PROHIBIT] Never use `TestModel` in production — it returns canned responses.
20. [PROHIBIT] Never hardcode API keys — use env vars (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc.).
21. [PROHIBIT] Never skip `result_type` validation — core safety feature of PydanticAI.
22. [PROHIBIT] Never use untyped `deps` — always specify `deps_type` for type safety.
[COMPAT]
- PydanticAI (latest, 2026).
- Durable execution: Temporal, DBOS, Prefect, Restate.
- MCP support: stdio, SSE, streamable HTTP.
- Models: OpenAI, Anthropic, Google, Groq, Mistral, Ollama, Bedrock.
- Python 3.10+ (3.14 compatible).
- Pydantic 2.0+ required.
[REFS]
- https://ai.pydantic.dev/
- https://github.com/pydantic/pydantic-ai
- https://ai.pydantic.dev/mcp/
- https://ai.pydantic.dev/durable-execution/
