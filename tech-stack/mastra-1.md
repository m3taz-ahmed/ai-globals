[TECH] Mastra v1.x
[OBJ] Mastra v1.x — TypeScript agent framework. Durable Agents / resumable streams (`createDurableAgent`, `createInngestAgent`), Inngest/Temporal-style workflow execution, tool approval/HITL, MCP stateless 2026-07-28, model timeout settings.
[RULES]
1. [REQ] Use Durable Agents for resumable streams: `createDurableAgent({ name, model, tools, instructions })`. Streams resume after disconnect/reconnect — state persisted via Inngest/Temporal-style engine.
2. [REQ] Use `createInngestAgent` for Inngest-backed durable execution: integrates with Inngest for step functions, retries, scheduling. `createInngestAgent({ inngest, ...agentConfig })`.
3. [REQ] Use Inngest/Temporal-style workflow execution: `workflow.step("name", async () => ...)` — durable steps with automatic retry, checkpointing, replay.
4. [REQ] Use tool approval / human-in-the-loop: `tool({ id, execute, requireApproval: true })`. Suspends execution, surfaces to user, resumes on approval. Configure via `suspend` / `resume`.
5. [REQ] Use MCP stateless support (2026-07-28 spec): `createMCPClient({ transport: "streamable_http", stateless: true })`. No session required — better for serverless/edge.
6. [REQ] Use model timeout settings: `model({ provider, name, timeout: 30000 })` — aborts request after N ms. Prevents hung LLM calls in production.
7. [REQ] Use `@mastra/core` for primitives: `Agent`, `Workflow`, `Step`, `Tool`, `Memory`. `import { Agent } from "@mastra/core"`.
8. [REQ] Use Mastra Cloud for managed deployment: `mastra deploy`. Includes observability, tracing, evals.
9. [REQ] Use `agent.stream(prompt)` for streaming: yields chunks with `text`, `tool_calls`, `tool_results`. Handle `for await (const chunk of stream)`.
10. [REQ] Use `agent.generate(prompt)` for non-streaming: returns full response with `text`, `toolCalls`, `usage`.
11. [REQ] Use structured output: `agent.generate(prompt, { output: zodSchema })` — returns validated Zod schema.
12. [REQ] Use memory: `agent.memory` with storage backends (Postgres, Redis, in-memory). `conversationId` for thread isolation.
13. [REQ] Use `registerApi` / `mastra.registerAgent` / `mastra.registerWorkflow` for service registration. Accessible via Mastra Cloud / API.
14. [REQ] Use `createTool({ id, description, inputSchema, execute })` for custom tools. Zod for input schema.
15. [REQ] Use `workflow.then(stepA).then(stepB)` or `workflow.step(...).branch(...)` for control flow. `.branch()` for conditional fan-out.
16. [CMD] `npm install @mastra/core` install core.
17. [CMD] `npx mastra init` scaffold new Mastra project.
18. [CMD] `npx mastra dev` run dev server with playground UI.
19. [PROHIBIT] Never use stateful MCP transport in serverless — use stateless (2026-07-28 spec).
20. [PROHIBIT] Never skip model `timeout` in production — hung LLM calls block workflows.
21. [PROHIBIT] Never hardcode API keys — use env vars / secrets manager.
22. [PROHIBIT] Never use in-memory storage for durable workflows in prod — use Postgres/Redis.
[COMPAT]
- Mastra v1.x (2026).
- Durable Agents: `createDurableAgent`, `createInngestAgent`.
- MCP stateless support (2026-07-28 spec).
- Inngest / Temporal-style workflow execution.
- Node.js 20+ / Bun / Deno.
- TypeScript 5.6+ (TS 6.0 compatible).
- Zod for schemas.
[REFS]
- https://mastra.ai/docs
- https://github.com/mastra-ai/mastra
- https://mastra.ai/docs/durable-agents
- https://mastra.ai/docs/mcp
