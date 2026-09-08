[TECH] Tailwind CSS 4.3
[OBJ] Tailwind CSS v4.3.x (latest 4.3.3, Jul 2026). Scrollbar utilities, `@container-size`, `zoom-*`, `tab-*`, stacked + compound `@variant`, `--default()` for functional utilities. v4.2 added 4 new palettes (mauve, olive, mist, taupe), logical properties, webpack plugin.
[RULES]
1. [REQ] Use scrollbar utilities: `scrollbar`, `scrollbar-thumb-*`, `scrollbar-track-*`, `scrollbar-gutter-*` — style scrollbars without browser-specific APIs.
2. [REQ] Use `@container-size` utility for size containers — container queries that care about height too, not just width.
3. [REQ] Use `zoom-*` utilities for CSS `zoom` property — now that all browsers support it.
4. [REQ] Use `tab-*` utilities to control rendered width of tab characters.
5. [REQ] Use stacked + compound `@variant` support — apply stacked and compound variants directly in CSS: `@variant dark hover`.
6. [REQ] Use `--default()` for functional utilities — define utilities that work with or without a value: `value(...) modifier(...)`.
7. [REQ] Use new color palettes from v4.2: mauve, olive, mist, taupe — expanded design token options.
8. [REQ] Use logical properties (v4.2+) — `ms-*`, `me-*`, `ps-*`, `pe-*` for direction-aware spacing.
9. [REQ] Use Oxide engine (Rust-based) — no config needed, PostCSS optional. `@theme` in CSS for config.
10. [REQ] Use `@container` (container queries), `@starting-style` (entry animations), subgrid.
11. [REQ] Use `animate-*` utilities + View Transitions. `motion-reduce:` mandatory for a11y.
12. [REQ] Use `text-shadow-*` utilities (v4.1+), `mask-*` utilities (v4.1+).
13. [PROHIBIT] Never use Tailwind 4.1 — EOL Feb 2026. Upgrade to 4.3+ immediately.
14. [PROHIBIT] Never use `tailwind.config.js` for v4+ — use `@theme` in CSS instead.
[COMPAT]
- Tailwind CSS 4.3.3 (released Jul 2026).
- v4.1 EOL: Feb 18, 2026 — no security patches.
- Engine: Oxide (Rust). No config needed. PostCSS optional.
- Browser support: Safari 16.4+ (modern browsers only).
[REFS]
- https://tailwindcss.com/blog/tailwindcss-v4-3
- https://github.com/tailwindlabs/tailwindcss/releases/tag/v4.3.3
- https://tailwindcss.com/docs
