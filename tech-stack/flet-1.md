[TECH] Flet 1.0
[OBJ] Flutter-engine UI in pure Python — one codebase to Windows/macOS/Linux/web/Android/iOS; Material+Cupertino adaptive widgets; production-ready since 1.0 (Sep 2026).
[RULES]
1. [REQ] Install: `pip install 'flet[all]'`; SDK requires Python >=3.10; `flet --version` verify; `flet run` dev loop, `flet build <target>` for artifacts.
2. [REQ] 1.0 model: handlers run on a single shared event loop (breaking change from 0.28 — don't mix old handler threading patterns); UI auto-refreshes after completed events (`yield` inside handlers streams intermediate updates); supports both imperative and declarative styles.
3. [REQ] Structure: `ft.app(target=main)`; `page` object = root; controls tree via `controls=[...]`/`Column`/`Row`/`Stack`; `expand`, `spacing`, `alignment` for responsive layout; `View`s + `page.route`/`page.go` for multi-page navigation.
4. [REQ] Theming: `page.theme = ft.Theme(color_scheme_seed=..., use_material3=True)` + `page.dark_theme` + `page.theme_mode`; `ft.Theme` nested `text_theme`/`color_scheme`/`visual_density`; one icon set (`ft.Icons` Material default or custom font).
5. [REQ] State: keep control refs via `ft.Ref[T]()` or by key/id; update via control property + `page.update()`/`control.update()`; shared state in a small state class or `page.session`/`page.client_storage` for persistence.
6. [REQ] Long work: `page.run_task`/`page.run_thread` for IO/CPU; `ft.ProgressBar`/`ft.ProgressRing` + streamed text via `yield` — never block the handler.
7. [REQ] Services (1.0): Audio, Geolocator, Clipboard, FilePicker etc. are persistent page services (`page.overlay`/`page.services`) — they survive reloads/navigation; init once.
8. [REQ] Build targets: `flet build windows|macos|linux|web|apk|aab|ipa|ios-simulator`; bundles Python 3.12/3.13/3.14 (Pyodide for web); web supports full-Wasm offline mode and HTML embedding.
9. [REQ] Migration (0.28→1.0): re-check handler signatures, event-loop semantics, renamed controls/props; run `flet migrate`/docs migration guide; pin `flet==1.0.*`.
10. [PROHIBIT] Never block handlers with `time.sleep`/sync requests — freezes UI; use async handlers or run_thread.
11. [PROHIBIT] No business logic inside control callbacks — services behind events.
12. [PROHIBIT] Never assume 0.28 API — 1.0 rewrote services + event loop; verify via Context7 `/flet-dev/flet`.
[COMPAT]
- Latest: 1.0.0 (Sep 2026, production-ready declaration). Apache-2.0.
- 150+ controls; extensions via Flutter packages bridge.
[REFS]
- https://flet.dev/docs/
- https://github.com/flet-dev/flet (examples; Flet Studio gallery)
