[TECH] NiceGUI 3.x
[OBJ] Python web UI on FastAPI + Vue/Quasar — `ui.*` element tree, per-client sessions, native-window mode via pywebview; ideal for tools, dashboards, IoT/robotics panels.
[RULES]
1. [REQ] Structure: `from nicegui import ui`; auto-index page vs `@ui.page('/route')` routes; shared layout via `ui.header`/`ui.left_drawer`/`ui.footer` context or `ui.sub_pages` (v3).
2. [REQ] State/binding: element `.bind_value(obj, 'attr')`/`.bind_visibility_from` two-way bindings; `app.storage.user|client|general` for persistence tiers; NEVER module-level mutable state for per-client data.
3. [REQ] Live updates: `ui.timer(interval, callback)`/`background_tasks` for polling/live data; `ui.run_javascript` sparingly; `ui.notify`/`ui.dialog` for feedback.
4. [REQ] Theming: `ui.colors(primary=..., secondary=..., accent=..., dark=...)`; `ui.dark_mode().bind_value(...)`; Tailwind via `.classes('...')`, Quasar props via `.props('dense outlined')`; CSS via `ui.add_head_html`/`ui.add_css`.
5. [REQ] Elements: `ui.table`/`ui.aggrid` for data screens (sortable/filterable props); `ui.echart`/`ui.plotly`/`ui.scene` (v3 modular object system) for viz; `ui.codemirror`/`ui.markdown`/`ui.log` for dev tools.
6. [REQ] Desktop mode: `ui.run(native=True, window_size=(w,h))` → pywebview window; `app.native.start_args` config; package via PyInstaller (include nicegui data files).
7. [REQ] Backend: FastAPI under the hood — mount APIRoutes, use `@app.get` for REST alongside UI; `ui.run_with(app)` to embed in existing FastAPI; auth via `app.storage.user` + middleware.
8. [REQ] v3 gotchas: `ui.scene` objects moved to `nicegui.elements.scene.objects`; `Object3D` requires `component=`; import patterns from v2 emit deprecation warnings — fix, don't silence.
9. [PROHIBIT] Never block the event loop — `run.io_bound`/`run.cpu_bound` for heavy work; async callbacks for IO.
10. [PROHIBIT] Don't reach into Vue internals per-element — props/classes escape hatch only where documented.
11. [PROHIBIT] No unauthenticated memory leaks — update ≥3.16.0 (GHSA-46f2-xhpw-8vh3 socket-disconnect fix, GHSA-955g-h32v-mvrr color-input XSS fix).
[COMPAT]
- Latest: 3.17.1 (Sep 2026); v3 line since late-2025; MIT; Python >=3.10.
- Update ≥3.16.0 mandatory for security fixes.
- Docs: https://nicegui.io — Context7 `/zauberzeug/nicegui`.
[REFS]
- https://github.com/zauberzeug/nicegui
- https://nicegui.io/documentation (examples gallery)
