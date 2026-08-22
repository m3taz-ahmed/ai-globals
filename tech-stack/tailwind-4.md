[TECH] tailwind-4
[OBJ] Tailwind CSS v4 — new Oxide engine, CSS-first config, @theme, OKLCH colors, container queries, 3D transforms.
[RULES]
1. [REQ] Architecture: Zero-config `@theme` in CSS. No `tailwind.config.js` needed for defaults. Use `@theme { --color-brand: oklch(0.65 0.2 250); }` for custom tokens. OKLCH color space for vibrant/accessible palettes.
2. [REQ] HTML: Extract repetitive utilities to Blade/React components (instead of `@apply`). Semantic HTML. Use `@apply` only for third-party CSS integration, not for internal component reuse.
3. [REQ] Responsive/A11y: Container Queries (`@container` / `@sm` / `@md` / `@lg`) over breakpoint media queries. Mobile-first. `focus:ring` / `focus:outline-none` MANDATORY for interactive elements.
4. [REQ] CSS-first configuration: use `@theme` directive in your main CSS file. Define custom colors, fonts, spacing, breakpoints as CSS custom properties. No JS config file required. Import via `@import "tailwindcss"`.
5. [REQ] Use `@utility` directive for custom utilities: `@utility tab-4 { tab-size: 4; }`. Custom utilities are tree-shaken like built-ins. Use `@variant` for custom variants: `@variant pointer-coarse (&:hover) { ... }`.
6. [REQ] OKLCH color space for all custom colors: `--color-primary: oklch(0.70 0.18 250)`. OKLCH provides perceptual uniformity — consistent lightness across hues. Use `oklch()` for dynamic color manipulation in `@theme`.
7. [REQ] Container queries: use `@container` on parent elements and `@sm:`, `@md:`, `@lg:`, `@xl:`, `@2xl:` on children. Container-based responsive design replaces viewport breakpoints for component-level layouts. Use `container-type: inline-size` via `@container` class.
8. [REQ] 3D transforms: use `transform-3d`, `rotate-x-*`, `rotate-y-*`, `rotate-z-*`, `perspective-*`, `transform-style-preserve-3d`, `backface-hidden`. Use for card flips, carousel depth, and interactive 3D UI. Test `perspective` values for natural depth.
9. [REQ] Use `@source` directive to specify content paths in CSS: `@source "../templates/**/*.blade.php"`. Replaces `content` array in JS config. Multiple `@source` lines for multiple globs.
10. [REQ] Use `@reference` directive for referencing theme values in custom CSS: `@reference --color-primary`. Enables autocompletion and validation of custom property references.
11. [REQ] Use the new Oxide engine (Rust-based) for 10x faster builds. No configuration needed — Oxide is the default engine in v4. Full builds and incremental HMR are significantly faster than v3.
12. [REQ] Use `data-*` variants for state-based styling: `data-[state=open]:block`, `data-[size=lg]:text-lg`. Replaces custom JS variant plugins for data-attribute-driven UI (accordions, dialogs, tabs).
13. [REQ] Use `@custom-variant` for reusable custom variants: `@custom-variant dark (&:where(.dark, .dark *));`. Supports nested selectors and pseudo-class composition.
14. [PROHIBIT] Never use `tailwind.config.js` for new v4 projects. Use CSS-first `@theme` config. JS config is legacy and will not receive new features.
15. [PROHIBIT] Never use `@apply` for component composition within the same project. Extract to Blade/React components instead. `@apply` is for third-party CSS bridge only.
16. [PROHIBIT] Never use hex/RGB colors for custom theme tokens. Use `oklch()` for perceptual uniformity and better dark-mode derivation.
[COMPAT]
- v4.0: Oxide engine (Rust), CSS-first config (`@import "tailwindcss"`), `@theme`, `@utility`, `@variant`, `@source`, `@custom-variant`. OKLCH default color space. Container queries built-in. 3D transforms. `data-*` variants.
- v3.x: Legacy JS config (`tailwind.config.js`). Still supported but no new features. Migrate to v4 CSS-first config.
- Frameworks: Vite (`@tailwindcss/vite`), PostCSS (`@tailwindcss/postcss`), Next.js 15 (built-in), Laravel 12+ (`@tailwindcss/vite`).
[REFS]
- https://tailwindcss.com/docs/v4-beta
- https://tailwindcss.com/blog/tailwindcss-v4
- https://tailwindcss.com/docs/theme
- https://tailwindcss.com/docs/container-queries
- https://tailwindcss.com/docs/transforms
- https://oklch.com/
