[TECH] Reflex 0.9
[OBJ] Full-stack web apps in pure Python — React frontend + FastAPI/Starlette backend generated from Python; `rx.State` event model + WebSocket sync; production tier for dashboards/tools/AI UIs.
[RULES]
1. [REQ] Structure: package layout `pages/`, `components/`, `state/`, `backend/` (services); `rxconfig.py` = app name, `db_url`, tailwind/theme config, env; `reflex init` scaffold.
2. [REQ] State model: ALL mutable state lives in `rx.State` subclasses; event handlers are methods mutating `self.*` vars; components reference `State.var` and re-render selectively — never module-level globals for per-user state.
3. [REQ] Long tasks: `@rx.event(background=True)` async handlers stream progress via `async with self:` mutations + `yield` (WebSocket push); token-streaming AI/LLM output uses background events — never blocking handlers.
4. [REQ] Theming: `rx.theme(appearance=, accent_color=, gray_color=, radius=, scaling=)`; `rx.color("accent", N)` tokens; Tailwind via `class_name="..."` escape hatch; dark/light via `appearance` + `rx.color_mode` toggle.
5. [REQ] Components: compose `rx.*` primitives; custom React only via `rx.Component`/wrapping (NoSSR when needed); `rx.cond` for conditional UI, `rx.foreach` for lists, `rx.moment` for dates.
6. [REQ] Data: `rx.Model` + SQLModel/SQLAlchemy for persistence; forms via `on_submit` events + `rx.toast` feedback; tables via `rx.data_table`/dataeditor component package.
7. [REQ] Pages/routes: `@rx.page(route=..., title=..., on_load=State.load)`; auth gate via `on_load` redirects; URL params via `rx.State` router vars.
8. [REQ] Production: `reflex run --env prod` (granian server); self-host Docker or Reflex Cloud; set `db_url` (SQLite dev → Postgres prod); Redis for multi-worker state; per-user session memory — size accordingly.
9. [REQ] Tests: unit-test `rx.State` event handlers as plain async methods; Playwright for E2E; keep components thin so state tests carry the logic.
10. [PROHIBIT] Never return early-rendered conditionals based on state at import time — state evaluates per-render via `rx.cond`.
11. [PROHIBIT] No secrets/business secrets in frontend vars — `rx.State` syncs to the browser; keep secrets in backend-only methods/env.
12. [PROHIBIT] Don't hand-edit generated `.web/` Next.js output — regenerate.
[COMPAT]
- Latest stable: 0.9.8.post1 (Aug 2026); 0.9.12 alphas current. Apache-2.0; Python >=3.10.
- Ships modular `reflex-components-*` packages (radix, lucide, recharts, sonner...).
- Docs: https://reflex.dev/docs — Context7 `/reflex-dev/reflex`.
[REFS]
- https://github.com/reflex-dev/reflex
- https://reflex.dev/templates/ (starter galleries)
