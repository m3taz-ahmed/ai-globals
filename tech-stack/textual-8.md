[TECH] Textual 8.x
[OBJ] Modern TUI framework by Textualize — Rich-based widgets, CSS (.tcss) styling, reactive state, async workers; runs in terminal AND browsers.
[RULES]
1. [REQ] Structure: `App` → `Screen` stack (`push_screen`/`switch_screen`) → `compose()` yields widgets; keep screens thin — logic in services.
2. [REQ] Styling: external `.tcss` files via `CSS_PATH` (not inline `styles=` for everything); define design tokens once (`$primary`, `$surface`, spacing vars); `Textual-dark`/custom `App.theme` for themes.
3. [REQ] State: `reactive`/`var` attributes + `watch_<name>` methods + `compute_<name>` for derived; `query_one`/`query` typed lookups instead of holding widget refs.
4. [REQ] Messages: custom `Message` classes bubble from widgets; handle via `on_<widget>_<msg>`/`@on` — decouple widgets from parents.
5. [REQ] Async: NEVER block the message pump — `@work(thread=True)` for CPU, `run_worker(..., exclusive=True)` for IO/tasks; `await asyncio.sleep` not `time.sleep`.
6. [REQ] Bindings: `BINDINGS = [("q","quit","Quit"), ...]` — every action keyboard-reachable; `CommandPalette` (Ctrl+\) for discoverability; footer shows keys for free.
7. [REQ] Tooling: `textual console` + `textual run --dev app.py` for live CSS reload + devtools; `textual keys` to debug key events; `textual diagnose`.
8. [REQ] Testing: `async with app.run_test() as pilot` for headless interaction tests; `pytest-textual-snapshot` for SVG snapshot regression.
9. [REQ] Serve: `textual-web`/`textual serve` exposes the same TUI in a browser — reuse for remote dashboards without rewriting to HTML.
10. [PROHIBIT] Never mutate UI from worker thread directly — use `call_from_thread`/`post_message` to hand results back to the app thread.
11. [PROHIBIT] No global mutable state for screen data — reactives + messages, not module-level dicts.
12. [CMD] `pip install "textual[dev]"` for devtools; `textual --version` check.
[COMPAT]
- Latest: 8.2.8 (Jun 2026); requires Python >=3.9, rich >=14.2.
- Optional `[syntax]` extras pull tree-sitter grammars (v8 line).
- Widget catalog + styles: https://textual.textualize.io/ — Context7 `/textualize/textual`.
[REFS]
- https://textual.textualize.io/
- https://github.com/Textualize/textual (examples/ dir — canonical widget patterns)
