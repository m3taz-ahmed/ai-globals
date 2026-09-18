---
name: design-md-lord
description: Lord skill for DESIGN.md-driven UI work — pick, import, and apply real-world brand design references (Refero catalog, 2000+ DESIGN.md files) through aiZee's DesignLibrary. Use when a UI task needs a concrete visual direction instead of generic AI styling.
triggers:
  - design.md
  - design system
  - brand design
  - refero
  - ui style reference
  - landing page design
  - dashboard design
  - pricing page
  - design tokens
  - تصميم
  - هوية بصرية
personas:
  - UX
  - UI
  - DEV
tech_stack:
  - tailwind-4-3
lord: true
---

# Design MD Lord

[OBJ] Apply real-world design references (DESIGN.md files — Refero catalog, brand systems) to UI work via aiZee's `DesignLibrary`. Extract tokens, typography, spacing, components, and Do/Don't rules from references — as inspiration, never verbatim copying.

[RULES]
1. [CMD] Browse the Refero catalog (styles.refero.design) for DESIGN.md references matching the project's vibe — 2000+ styles extracted from real sites.
2. [CMD] With the Refero MCP server configured (`refero` in `.devin/mcp_config.json`), search styles semantically instead of guessing.
3. [CMD] Import a reference into the local library: `DesignLibrary.import_brand(name, source)` accepts a `DESIGN.md` path or raw markdown — lands in `design-library/<name>/DESIGN.md` and loads immediately.
4. [CMD] Load + mix references: `DesignLibrary.load("apple")`, `.mix(["stripe", "linear"])` for cross-brand fusion, `.suggest(project_type)` for recommendations, `.detect_project_type(dir)` to auto-detect.
5. [REQ] Match reference to page type: landing/hero → bold brands (Linear, Vercel, Framer); dashboard/SaaS → density-first (Linear, Stripe, Sentry); pricing → conversion-focused (Stripe, Cal.com); docs → readability-first (Vercel, Notion); mobile → Apple/Google HIG.
6. [REQ] Extract, don't copy: pull semantic tokens (`--color-*` + role), type scale, spacing rhythm, radii, shadows, component patterns, and the Do/Don't rules — then apply to THIS project's design system, not a clone.
7. [REQ] Token discipline: every color/spacing/type choice must trace to a token in the reference or the project's `@theme`. NEVER invent ad-hoc values outside the token system.
8. [REQ] Honor the reference's Do/Don't section — it encodes what makes the style work (e.g., Apple's restraint, Linear's density, Stripe's elevation).
9. [REQ] Mix at most 2-3 references: colors/components/elevation from one, typography/layout from another. More sources = incoherent slop.
10. [PROHIBIT] Never copy brand names, logos, or trademarked assets — references guide style only.
11. [REQ] After applying, run `DesignSlopVerifier` — references prevent generic-AI output only if actually followed.
12. [REQ] RTL/Arabic projects: prefer references with clean geometric type; verify logical-property friendliness of spacing tokens.

[WORKFLOWS]
1. New page design: detect project type → `suggest()` or search Refero → pick 1-2 references → `import_brand()` → `load()`/`mix()` → extract tokens → map to `@theme`/components → build → `DesignSlopVerifier` → a11y pass.
2. Import a Refero style: find style on styles.refero.design (or MCP search) → copy `DESIGN.md` content → `DesignLibrary.import_brand("<name>", <content>)` → use like any catalog brand.
3. Refresh a stale UI: `detect_project_type()` → suggest modern references → diff current tokens vs reference → update `@theme` → verify components pick up tokens.
