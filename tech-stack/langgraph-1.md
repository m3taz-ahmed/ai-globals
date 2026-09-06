[TECH] LangGraph 1.1
[OBJ] LangGraph 1.1 (Mar 2026). `version="v2"` type-safe streaming/invoke, StateSchema, ReducedValue, UntrackedValue, MessagesValue, durable checkpoints, human-in-the-loop, subgraph replay.
[RULES]
1. [REQ] Use `version="v2"` for type-safe streaming + invoke: `graph.invoke(input, version="v2")` / `graph.stream(input, version="v2")`. v2 returns typed `StreamEvent` objects with full type safety.
2. [REQ] Define state with `StateSchema`: `class MyState(StateSchema): messages: MessagesValue; count: ReducedValue[int]`. Typed, validated, replaces `TypedDict` state.
3. [REQ] Use `ReducedValue` for reducer-backed state fields: `ReducedValue[int](reducer=add)` — values merged across parallel branches via reducer function.
4. [REQ] Use `UntrackedValue` for ephemeral state (not checkpointed): `UntrackedValue[dict]` — excluded from persistence, reduces checkpoint size.
5. [REQ] Use `MessagesValue` for chat message lists: auto-appends, handles message ID dedup, supports `add_messages` reducer semantics.
6. [REQ] Use durable checkpoints for persistence: `MemorySaver` (dev), `SqliteSaver` / `PostgresSaver` (prod). Enables resume after crash/restart.
7. [REQ] Use human-in-the-loop via `interrupt()`: pause execution, surface state to user, resume with `Command(resume=user_input)`. Configure `interrupt_before` / `interrupt_after` on nodes.
8. [REQ] Use subgraph replay: replay execution from checkpoint with modified inputs. `graph.invoke(None, config={"configurable": {"thread_id": tid}})` resumes from last checkpoint.
9. [REQ] Use `StateGraph(StateSchema)` to define graph: `graph.add_node("name", fn)`, `graph.add_edge("a", "b")`, `graph.add_conditional_edges("node", router_fn)`.
10. [REQ] Use `graph.compile(checkpointer=..., interrupt_before=...)` to finalize graph. Compiled graph is immutable.
11. [REQ] Use `langgraph.prebuilt` for common patterns: `create_react_agent` (ReAct agent), `create_tool_node` (tool execution).
12. [REQ] Use `Send` for dynamic fan-out: `return [Send("node", {"input": x}) for x in items]` — parallel branch per item.
13. [REQ] Use `Command` for explicit control flow: `Command(goto="node", update={"key": value})` — replaces return-dict routing.
14. [REQ] Use `langgraph-sdk` for deployment to LangGraph Platform (managed): `langgraph deploy`. Includes Studio UI for debugging.
15. [REQ] Use `langgraph.checkpoint` for custom checkpointers: implement `BaseCheckpointSaver` interface. Use Redis/Postgres for prod.
16. [CMD] `pip install langgraph` install core.
17. [CMD] `pip install langgraph-sdk` install SDK for LangGraph Platform.
18. [CMD] `langgraph dev` run local dev server with Studio UI.
19. [PROHIBIT] Never use `version="v1"` for new code — v2 is type-safe and recommended.
20. [PROHIBIT] Never mutate state directly — return updates from node functions (reducer pattern).
21. [PROHIBIT] Never use `MemorySaver` in production — use persistent checkpoint (Postgres/Sqlite/Redis).
22. [PROHIBIT] Never compile graph multiple times — compile once, invoke many.
[COMPAT]
- LangGraph 1.1 (Mar 2026).
- `version="v2"` streaming/invoke (type-safe).
- StateSchema, ReducedValue, UntrackedValue, MessagesValue.
- LangChain 1.3 integration.
- Python 3.10+ (3.14 compatible).
- LangGraph Platform for managed deployment.
[REFS]
- https://langchain-ai.github.io/langgraph/
- https://langchain-ai.github.io/langgraph/concepts/low_level/
- https://github.com/langchain-ai/langgraph
- https://docs.langchain.com/oss/python/langgraph
