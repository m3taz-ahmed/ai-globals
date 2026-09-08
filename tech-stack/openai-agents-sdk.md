[TECH] OpenAI Agents SDK v0.22
[OBJ] OpenAI Agents SDK v0.22 (latest 0.22.0, Aug 2026). Replaces Swarm. Any-LLM adapter, MCP resource support, tool use, handoffs, guardrails, tracing, sandboxed execution, multi-agent orchestration. Default model changed to gpt-5.6-luna (pin explicitly).
[RULES]
1. [REQ] Use `openai-agents` package (v0.22+): `from agents import Agent, Runner`. Replaces experimental `openai-swarm` package — migrate all Swarm code.
2. [REQ] PIN MODEL EXPLICITLY: v0.20+ changed default model to `gpt-5.6-luna` (nano-tier) without deprecation notice. Always pass `model=` explicitly in Agent config. Lock SDK version in `pyproject.toml`.
3. [REQ] Use sandboxed execution (v0.21.1+): persistent workspace for filesystem ops, command execution, state surviving between runs. Use for agent file/command tools.
4. [REQ] Use any-LLM adapter for non-OpenAI models: `from agents.extensions.models import BaseModelProvider` or provider-specific adapters (Anthropic, Google, Bedrock). Configure via `model=` param.
5. [REQ] Use MCP resource support: `from agents.mcp import MCPServerStdio, MCPServerSSE`. Agents can access MCP tools/resources: `agent = Agent(name=..., mcp_servers=[server])`.
6. [REQ] Define agents with `Agent(name=..., instructions=..., tools=..., model=...)`. Instructions are system prompt; tools are function tools or MCP tools.
7. [REQ] Use handoffs for agent-to-agent delegation: `agent = Agent(name=..., handoffs=[other_agent])`. Handoff transfers conversation control to target agent.
8. [REQ] Use guardrails for input/output validation: `agent = Agent(name=..., input_guardrails=[...], output_guardrails=[...])`. Guardrails run in parallel, abort on failure.
9. [REQ] Use tracing for observability: `from agents import trace`. Auto-traced by default — view in OpenAI Dashboard or export to Langfuse/LangSmith.
10. [REQ] Isolate usage accounting between `RunState` checkpoints (v0.22+). Terminal function-tool output blocked by output guardrails is redacted from replay/persisted state.
11. [REQ] Use sessions for automatic conversation history. Use `Runner.run()` with session state for multi-turn conversations.
12. [REQ] Use realtime agents for voice/audio: `from agents import RealtimeAgent`. Supports voice-based multi-agent workflows.
8. [REQ] Use function tools: `@agent.tool` decorator on methods or `tools=[function1, function2]`. SDK auto-generates schema from signature/docstring.
9. [REQ] Use `Runner.run(agent, input)` for async execution. `Runner.run_sync()` for sync. `Runner.run_streamed()` for streaming output.
10. [REQ] Use `agent.with_structured_output(Schema)` for typed agent responses — returns Pydantic model.
11. [REQ] Use `RunConfig` for execution config: `Runner.run(agent, input, run_config=RunConfig(max_turns=10, trace_name="..."))`.
12. [REQ] Use `context` for shared state across agents: `context = MyContext(...)`, pass to `Runner.run(agent, input, context=context)`. Access via `ctx` param in tools.
13. [REQ] Use `agent.as_tool()` to wrap an agent as a callable tool for another agent — enables hierarchical multi-agent patterns.
14. [REQ] Use lifecycle hooks: `from agents import AgentHooks`. `on_start`, `on_end`, `on_handoff`, `on_tool_start`, `on_tool_end` for side-effects.
15. [REQ] Use `parallel_tool_calls=True` on agent for concurrent tool execution (default True in v0.13).
16. [CMD] `pip install openai-agents` install SDK.
17. [CMD] `npm install @openai/agents` install Node SDK (if available).
18. [CMD] `agents run agent.py` run agent script (CLI).
19. [PROHIBIT] Never use `openai-swarm` — deprecated, replaced by `openai-agents`.
20. [PROHIBIT] Never hardcode API keys — use `OPENAI_API_KEY` env or provider-specific env.
21. [PROHIBIT] Never skip guardrails in production — validate inputs/outputs for safety.
22. [PROHIBIT] Never run unbounded `max_turns` — set limit to prevent infinite loops.
[COMPAT]
- OpenAI Agents SDK v0.13+.
- Replaces openai-swarm (deprecated).
- Any-LLM adapter: OpenAI, Anthropic, Google, Bedrock, Azure.
- MCP support: stdio, SSE, streamable HTTP.
- Python 3.9+ (3.14 compatible).
- Tracing: OpenAI Dashboard, Langfuse, LangSmith.
[REFS]
- https://openai.github.io/openai-agents-python/
- https://github.com/openai/openai-agents-python
- https://platform.openai.com/docs/guides/agents
- https://modelcontextprotocol.io/
