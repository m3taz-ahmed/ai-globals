[TECH] Agent-to-Agent (A2A) Protocol
[OBJ] A2A Protocol — inter-agent task coordination. Agent cards, task lifecycle, streaming updates, push notifications. Complements MCP (tools) with agent-to-agent communication.
[RULES]
1. [REQ] Use A2A Protocol for inter-agent communication: one agent delegates tasks to another agent (potentially on different framework/vendor). Complements MCP — MCP exposes tools, A2A exposes agents.
2. [REQ] Publish agent cards at `/.well-known/agent.json`: JSON metadata with `name`, `description`, `capabilities`, `skills`, `authentication`, `endpoints`. Enables discovery.
3. [REQ] Use task lifecycle: `submitted` → `working` → `input-required` → `completed` / `failed` / `canceled`. Client polls or streams for status updates.
4. [REQ] Use `tasks/send` to create/update a task. Use `tasks/sendSubscribe` for streaming (SSE) — server pushes `TaskStatusUpdateEvent` + `TaskArtifactUpdateEvent`.
5. [REQ] Use push notifications for async updates: `tasks/send` with `pushNotificationConfig` — server sends webhook on status change. Configure `webhook` URL + auth token.
6. [REQ] Use `tasks/get` to poll task status. Use `tasks/cancel` to cancel. Use `tasks/resubscribe` to reconnect to SSE stream.
7. [REQ] Use artifacts for task outputs: `Artifact(name, parts, index)`. Parts can be `TextPart`, `FilePart`, `DataPart`. Multiple artifacts per task.
8. [REQ] Use `messages` within tasks for multi-turn: `Message(role="user"|"agent", parts=[...])`. Enables clarification + input-required flows.
9. [REQ] Use `TaskState.input-required` to pause for user/agent input: client sends `tasks/send` with new message to resume.
10. [REQ] Use authentication in agent card: `authentication: {schemes: ["bearer", "oauth2", "api_key"]}`. Client must authenticate before `tasks/send`.
11. [REQ] Use `AgentCard.skills` to advertise agent capabilities: `Skill(id, name, description, tags, inputModes, outputModes)`. Clients match skills to task requirements.
12. [REQ] Use JSON-RPC 2.0 as transport protocol (over HTTP/SSE). `{"jsonrpc": "2.0", "method": "tasks/send", "params": {...}, "id": "..."}`.
13. [REQ] Use A2A + MCP together: A2A for agent-to-agent delegation, MCP for tool/resource access. An agent can be both an A2A server (receives tasks) and MCP client (uses tools).
14. [REQ] Use `a2a-sdk` (Python) or `@a2a/protocol` (Node.js) for server/client implementation. `from a2a.server import A2AServer`.
15. [REQ] Use streaming for long-running tasks: `tasks/sendSubscribe` returns SSE stream. Parse `event: status` / `event: artifact` events.
16. [CMD] `pip install a2a-sdk` install Python SDK.
17. [CMD] `npm install @a2a/protocol` install Node SDK.
18. [CMD] `curl http://agent-host/.well-known/agent.json` discover agent card.
19. [PROHIBIT] Never use A2A for simple tool calls — use MCP. A2A is for agent-to-agent task delegation.
20. [PROHIBIT] Never expose agent card without authentication requirements — secure endpoints.
21. [PROHIBIT] Never skip `pushNotificationConfig` auth token — webhook must be authenticated.
22. [PROHIBIT] Never block on `tasks/get` polling — use streaming or push notifications for long tasks.
[COMPAT]
- A2A Protocol (Google-led, open standard, 2025-2026).
- Transport: JSON-RPC 2.0 over HTTP + SSE.
- Complements MCP (tools) — A2A for agents, MCP for tools.
- SDKs: a2a-sdk (Python), @a2a/protocol (Node.js).
- Frameworks: LangChain, CrewAI, AutoGen, Mastra, PydanticAI support A2A.
[REFS]
- https://a2a-protocol.org/
- https://github.com/a2aproject/a2a
- https://a2a-protocol.org/latest/specification/
- https://google.github.io/A2A/
