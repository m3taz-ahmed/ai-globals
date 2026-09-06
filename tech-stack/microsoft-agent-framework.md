[TECH] Microsoft Agent Framework 1.0
[OBJ] Microsoft Agent Framework 1.0 GA (Apr 2026). Replaces AutoGen (now community-maintained, use AG2 fork). Multi-agent orchestration, durable execution, MCP support, tracing.
[RULES]
1. [REQ] Use `microsoft-agents` package (v1.0+ GA): `from microsoft_agents import Agent, Team`. Replaces `autogen` — migrate all AutoGen code. AutoGen is now community-maintained; use AG2 fork for legacy.
2. [REQ] Use multi-agent orchestration: `Team` with `RoundRobinGroupChat`, `SelectorGroupChat`, `Swarm`, `MagenticOne`. Orchestrate via `team.run(task, max_turns=N)`.
3. [REQ] Use durable execution: checkpoint agent state for resume/replay. Integrate with Azure Durable Functions / Semantic Kernel process framework.
4. [REQ] Use MCP support: `from microsoft_agents.mcp import MCPServer`. Agents access MCP tools/resources via `agent.mcp_servers=[server]`.
5. [REQ] Use tracing: OpenTelemetry-compatible. Export to Azure Application Insights, Langfuse, or any OTLP collector. `configure_tracing(exporter=...)`.
6. [REQ] Define agents with `Agent(name=..., model=..., instructions=..., tools=...)`. Use `AzureChatCompletionsModel` or `OpenAIChatCompletionsModel` or any-LLM.
7. [REQ] Use function tools: `@agent.tool` decorator. Auto-schema from type hints + docstrings. `@agent.tool_plain` for no-context tools.
8. [REQ] Use `agent.run(task)` / `agent.run_stream(task)` for execution. Returns `TaskResult` with messages, usage, stop reason.
9. [REQ] Use `Team` patterns: `RoundRobinGroupChat(agents)` (sequential), `SelectorGroupChat(agents, selector_func=...)` (LLM picks next speaker), `Swarm(agents)` (handoff-based).
10. [REQ] Use `MagenticOne` for complex multi-agent reasoning: auto-orchestrates planner + researcher + coder + executor. `team = MagenticOne(model=...)`.
11. [REQ] Use `agent.with_structured_output(PydanticModel)` for typed responses.
12. [REQ] Use `Termination` conditions: `MaxMessageTermination(10)`, `TextMentionTermination("TERMINATE")`, `TokenUsageTermination(...)`. Combine with `|` / `&`.
13. [REQ] Use `CodeExecutorAgent` / `DockerCodeExecutor` for sandboxed code execution. Never run untrusted code without sandbox.
14. [REQ] Use `agent.memory` for conversation persistence: `BufferedChatMemory`, `SummarizedChatMemory`. Integrate with vector stores for RAG.
15. [REQ] Use Azure AI Foundry for managed deployment: `azure-ai-projects` SDK. Includes model catalog, evals, safety filters.
16. [CMD] `pip install microsoft-agents` install Python SDK.
17. [CMD] `npm install @microsoft/agents` install Node SDK (if available).
18. [CMD] `az login` authenticate with Azure for Azure AI Foundry integration.
19. [PROHIBIT] Never use `autogen` package for new code — use `microsoft-agents` or AG2 fork.
20. [PROHIBIT] Never run untrusted code without `DockerCodeExecutor` sandbox.
21. [PROHIBIT] Never hardcode API keys — use env vars / Azure Key Vault / Managed Identity.
22. [PROHIBIT] Never skip `max_turns` / termination conditions — prevent infinite agent loops.
[COMPAT]
- Microsoft Agent Framework 1.0 GA (Apr 2026).
- Replaces AutoGen (community-maintained, use AG2 fork for legacy).
- Models: Azure OpenAI, OpenAI, Anthropic, Google (via adapters).
- MCP support: stdio, SSE, streamable HTTP.
- Python 3.10+ (3.14 compatible).
- Azure AI Foundry integration.
- OpenTelemetry tracing.
[REFS]
- https://github.com/microsoft/agent-framework
- https://learn.microsoft.com/en-us/azure/ai-services/agents/
- https://microsoft.github.io/agent-framework/
- https://github.com/microsoft/autogen (legacy, community-maintained)
