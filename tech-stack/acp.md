[TECH] Agent Connection Protocol (ACP)
[OBJ] Standardizes agent-to-agent communication — complements MCP (tools) and A2A (tasks). Defines connection lifecycle, capability negotiation, message routing.
[RULES]
1. [REQ] Use ACP for agent-to-agent connection standardization — complements MCP (tool access) and A2A (task delegation).
2. [REQ] ACP defines connection lifecycle: initiate → negotiate → establish → message → terminate. Follow lifecycle states explicitly.
3. [REQ] Use capability negotiation during connection establishment — agents advertise capabilities (protocols, message types, formats) before messaging.
4. [REQ] Use message routing per ACP spec — route messages based on agent identity + capability match.
5. [REQ] Use ACP alongside MCP — MCP for tool access, A2A for task delegation, ACP for connection management.
6. [REQ] Implement ACP connection handlers: `onConnect`, `onDisconnect`, `onMessage`, `onCapabilityNegotiation`.
7. [REQ] Use unique agent identifiers (DID/URI format) for routing — never reuse identifiers across agents.
8. [REQ] Use structured message envelopes: `sender`, `recipient`, `type`, `payload`, `metadata`, `correlationId`.
9. [REQ] Handle connection failures gracefully — retry with backoff, notify upstream, log correlation IDs.
10. [REQ] Use ACP for multi-agent orchestration topologies: hub-spoke, peer-to-peer, mesh.
11. [REQ] Version ACP protocol in message headers — `protocol: "acp", version: "1.0"`.
12. [PROHIBIT] Never use ACP for tool access — use MCP. Never use ACP for task delegation — use A2A.
13. [PROHIBIT] Never skip capability negotiation — messaging without negotiation leads to protocol mismatches.
14. [PROHIBIT] Never hardcode agent addresses — use registry/discovery service.
15. [PROHIBIT] Never send unstructured messages — use ACP envelope format.
16. [PROHIBIT] Never ignore connection termination — clean up resources, notify dependents.
17. [REQ] Use ACP in combination with OpenTelemetry tracing — trace connection lifecycle spans.
18. [REQ] Use ACP security: mutual authentication, encrypted channels, capability-scoped authorization.
19. [REQ] Use ACP for HITL (human-in-the-loop) gates — route human-agent connections through ACP lifecycle.
20. [PROHIBIT] Never assume ACP replaces MCP or A2A — they are complementary, not overlapping.
[COMPAT]
- ACP: agent-to-agent connection protocol.
- Complements: MCP (tools), A2A (tasks).
- Protocol versioning: header-based.
- Agent identifiers: DID/URI format.
- OpenTelemetry tracing compatible.
[REFS]
- https://agentconnectionprotocol.org/ (speculative — verify)
- https://modelcontextprotocol.io/ (MCP)
- https://a2a-protocol.org/ (A2A)
