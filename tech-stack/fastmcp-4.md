[TECH] FastMCP v4.0.0 (GA 31 Aug 2026)
[OBJ] MCP server framework — builds on Python SDK v2, multi-era client negotiation (2026-07-28 + legacy), stateless UserSession, multi-round-trip elicitation, `fastmcp.Client`, enterprise identity, extensions, `fastmcp-tasks`, auth providers, middleware.
[RULES]
1. [REQ] FastMCP v4 builds on Python SDK v2 — `pip install fastmcp==4.0.0`; ensure Python 3.10+.
2. [REQ] Support modern (2026-07-28) + legacy MCP clients via multi-era negotiation — FastMCP auto-detects client protocol version.
3. [REQ] Use stateless `UserSession` — session state passed per-request, no server-side session storage required.
4. [REQ] Use multi-round-trip elicitation — `ctx.elicit()` supports back-and-forth user input across multiple round trips.
5. [REQ] Use `fastmcp.Client` for client-side MCP connections — `async with fastmcp.Client("http://server/sse") as client: ...`.
6. [REQ] Use enterprise identity providers — OAuth2/OIDC integration via auth providers.
7. [REQ] Use authentication providers: `fastmcp.server.auth.OAuthProvider`, `BearerAuthProvider` — configure in `FastMCP(auth=...)`.
8. [REQ] Use middleware for cross-cutting concerns — `FastMCP(middleware=[LoggingMiddleware(), RateLimitMiddleware()])`.
9. [REQ] Use `fastmcp-tasks` for background work — long-running tasks offloaded from request cycle.
10. [REQ] Use extensions for custom protocol features — register extension handlers via `server.add_extension()`.
11. [REQ] Most FastMCP 3 servers upgrade mechanically — bump version, review deprecation warnings, test.
12. [REQ] Use `@mcp.tool()` decorator for tool registration — type hints auto-generate schema.
13. [REQ] Use `@mcp.resource()` for resource endpoints — URI templates supported.
14. [REQ] Use `@mcp.prompt()` for prompt templates — parameterized prompts with type-safe args.
15. [PROHIBIT] Never use server-side session storage — use stateless `UserSession`.
16. [PROHIBIT] Never hardcode auth credentials — use auth providers + env vars.
17. [PROHIBIT] Never block request cycle with long-running tasks — use `fastmcp-tasks`.
18. [PROHIBIT] Never assume single-era client — always support multi-era negotiation.
19. [CMD] `pip install fastmcp==4.0.0` — install.
20. [CMD] `fastmcp run server.py` — run server.
[COMPAT]
- FastMCP v4.0.0: GA 31 Aug 2026.
- Python SDK v2 foundation.
- Client protocol: 2026-07-28 (modern) + legacy era negotiation.
- `fastmcp-tasks`: background task extension.
- Auth: OAuth2/OIDC providers, bearer token.
- Middleware: pluggable request pipeline.
- FastMCP 3 → 4: mechanical upgrade for most servers.
[REFS]
- https://gofastmcp.com/
- https://github.com/jlowin/fastmcp
- https://gofastmcp.com/deployments
- https://modelcontextprotocol.io/
