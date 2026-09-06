[TECH] Durable Execution Patterns
[OBJ] Crash/disconnect-resilient agent workflows — Temporal (workflow-as-code), Inngest (serverless durable functions), DBOS (Python durable workflows), Prefect (data pipelines), Restate (durable services). HITL gates, long-running tasks.
[RULES]
1. [REQ] Use durable execution for crash/disconnect-resilient agent workflows — state persists across process restarts, network failures.
2. [REQ] Use Temporal for workflow-as-code: durable timers, retries, saga patterns. `@workflow.defn` + `@workflow.run` in Python/Go/TS.
3. [REQ] Use Inngest for serverless durable functions: `step.run()`, `step.sleep()`, `step.waitForEvent()` — event-driven, no infra.
4. [REQ] Use DBOS for Python durable workflows: `@DBOS.step()` decorators — checkpoint state in Postgres.
5. [REQ] Use Prefect for data pipeline orchestration: `@flow` + `@task` decorators — Dask/Ray integration.
6. [REQ] Use Restate for durable services: virtual objects, event-driven, stateful — Rust/TS/Python SDKs.
7. [REQ] Use durable timers (`step.sleep()`, `workflow.sleep()`) instead of `setTimeout` / `asyncio.sleep` — survive restarts.
8. [REQ] Use HITL (human-in-the-loop) gates: `step.waitForEvent("human.approval")` / `workflow.wait_for_signal()` — pause until human input.
9. [REQ] Use idempotent step functions — duplicate execution must produce same result (at-least-once delivery).
10. [REQ] Use retries with exponential backoff on step/workflow failures — configure max attempts + backoff.
11. [REQ] Use compensation/saga patterns for multi-step workflows — rollback on failure.
12. [REQ] Use durable execution for long-running tasks (minutes/hours/days) — never use in-memory state for >60s tasks.
13. [REQ] Choose by use case: Temporal (full control, self-hosted/cloud), Inngest (serverless, event-driven), DBOS (Python, Postgres), Prefect (data pipelines), Restate (durable microservices).
14. [PROHIBIT] Never use in-memory state for long-running agent workflows — use durable execution.
15. [PROHIBIT] Never use `setTimeout` / `asyncio.sleep` for durable delays — use `step.sleep()` / `workflow.sleep()`.
16. [PROHIBIT] Never assume step functions execute exactly-once — design for at-least-once (idempotent).
17. [PROHIBIT] Never skip retry configuration — always set max attempts + backoff.
18. [PROHIBIT] Never block workflow execution on synchronous human input without durable wait — use signals/events.
19. [CMD] Temporal: `temporal workflow start --type MyWorkflow --taskqueue my-queue` — start workflow.
20. [CMD] Inngest: `npx inngest-cli dev` — local dev server.
[COMPAT]
- Temporal: Python, Go, TypeScript, Java SDKs.
- Inngest: TypeScript, Python SDKs; serverless (Vercel/Cloudflare/AWS).
- DBOS: Python; Postgres checkpointing.
- Prefect: Python; Dask/Ray integration.
- Restate: Rust, TypeScript, Python SDKs.
- All: idempotent steps, durable timers, HITL gates.
[REFS]
- https://temporal.io/
- https://www.inngest.com/
- https://dbos.dev/
- https://prefect.io/
- https://restate.dev/
