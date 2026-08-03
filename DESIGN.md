---
version: alpha
name: ai-global-os-dashboard-design
description: Design language for the AI Global OS dashboard — a sovereign AI engineering control plane. Dark-first, data-dense, command-palette driven, with a command-center aesthetic. Built around deep charcoal-lapis surfaces, electric-cyan accent for AI state, violet for memory/knowledge, lime for success/allowed actions, and amber/red for warnings and policy blocks. UI fonts are Geist/Inter; code is JetBrains Mono. Layout is a left navigation rail, global command palette, and bento-grid metric cards.

colors:
  canvas: "#0a0a0f"
  surface-1: "#12131a"
  surface-2: "#181a22"
  surface-3: "#1e2029"
  surface-elevated: "#252833"
  surface-glass: "rgba(18, 19, 26, 0.72)"
  primary: "#22d3ee"
  primary-hover: "#67e8f9"
  primary-focus: "#06b6d4"
  on-primary: "#0a0a0f"
  accent-violet: "#8b5cf6"
  accent-violet-soft: "rgba(139, 92, 246, 0.16)"
  accent-lime: "#a3e635"
  accent-amber: "#f59e0b"
  accent-red: "#ef4444"
  ink: "#f7f8f8"
  ink-muted: "#9ca3af"
  ink-faint: "#6b7280"
  hairline: "#2a2d38"
  hairline-strong: "#3f4352"
  hairline-subtle: "#1c1e25"
  inverse-canvas: "#ffffff"
  inverse-surface-1: "#f3f4f6"
  inverse-ink: "#111827"


typography:
  display-hero:
    fontFamily: "Geist, Inter, -apple-system, system-ui, sans-serif"
    fontSize: "56px"
    fontWeight: 600
    lineHeight: 1.1
    letterSpacing: "-1.5px"
  display-lg:
    fontFamily: "Geist, Inter, -apple-system, system-ui, sans-serif"
    fontSize: "40px"
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: "-1px"
  headline:
    fontFamily: "Geist, Inter, -apple-system, system-ui, sans-serif"
    fontSize: "28px"
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: "-0.5px"
  card-title:
    fontFamily: "Geist, Inter, -apple-system, system-ui, sans-serif"
    fontSize: "18px"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "-0.2px"
  subhead:
    fontFamily: "Inter, -apple-system, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 500
    lineHeight: 1.4
  body-lg:
    fontFamily: "Inter, -apple-system, system-ui, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.6
  body:
    fontFamily: "Inter, -apple-system, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
  body-sm:
    fontFamily: "Inter, -apple-system, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.5
  caption:
    fontFamily: "Inter, -apple-system, system-ui, sans-serif"
    fontSize: "12px"
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: "0.2px"
  button-cap:
    fontFamily: "Inter, -apple-system, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "0.1px"
  code:
    fontFamily: "JetBrains Mono, Fira Code, Consolas, Monaco, monospace"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.6
  code-strong:
    fontFamily: "JetBrains Mono, Fira Code, Consolas, Monaco, monospace"
    fontSize: "13px"
    fontWeight: 700
    lineHeight: 1.6

rounded:
  none: "0px"
  xs: "4px"
  sm: "6px"
  md: "8px"
  lg: "12px"
  xl: "16px"
  full: "9999px"

spacing:
  xxs: "2px"
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
  xxl: "32px"
  section: "64px"

components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.button-cap}"
    rounded: "{rounded.md}"
    padding: "10px 16px"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    border: "1px solid {colors.hairline}"
    typography: "{typography.button-cap}"
    rounded: "{rounded.md}"
    padding: "10px 16px"
  button-icon:
    backgroundColor: "{colors.surface-2}"
    textColor: "{colors.ink-muted}"
    rounded: "{rounded.md}"
    padding: "8px"
  card:
    backgroundColor: "{colors.surface-1}"
    border: "1px solid {colors.hairline}"
    rounded: "{rounded.lg}"
    padding: "16px"
  card-elevated:
    backgroundColor: "{colors.surface-glass}"
    border: "1px solid {colors.hairline}"
    backdropFilter: "blur(12px)"
    rounded: "{rounded.lg}"
    padding: "16px"
  metric-card:
    backgroundColor: "{colors.surface-2}"
    border: "1px solid {colors.hairline}"
    rounded: "{rounded.lg}"
    padding: "16px"
  command-palette:
    backgroundColor: "{colors.surface-elevated}"
    border: "1px solid {colors.hairline-strong}"
    rounded: "{rounded.xl}"
    padding: "16px"
  status-pill-success:
    backgroundColor: "rgba(163, 230, 53, 0.12)"
    textColor: "{colors.accent-lime}"
    typography: "{typography.caption}"
    rounded: "{rounded.full}"
    padding: "4px 10px"
  status-pill-warning:
    backgroundColor: "rgba(245, 158, 11, 0.12)"
    textColor: "{colors.accent-amber}"
    typography: "{typography.caption}"
    rounded: "{rounded.full}"
    padding: "4px 10px"
  status-pill-danger:
    backgroundColor: "rgba(239, 68, 68, 0.12)"
    textColor: "{colors.accent-red}"
    typography: "{typography.caption}"
    rounded: "{rounded.full}"
    padding: "4px 10px"
  code-block:
    backgroundColor: "{colors.surface-2}"
    textColor: "{colors.ink}"
    typography: "{typography.code}"
    rounded: "{rounded.md}"
    padding: "12px 16px"
  log-line:
    backgroundColor: "transparent"
    textColor: "{colors.ink-muted}"
    typography: "{typography.code}"
    borderLeft: "2px solid {colors.hairline}"
    padding: "6px 0 6px 12px"
  nav-rail:
    backgroundColor: "{colors.surface-1}"
    border: "1px solid {colors.hairline}"
    rounded: "{rounded.none}"
    padding: "12px"
  toast:
    backgroundColor: "{colors.surface-elevated}"
    textColor: "{colors.ink}"
    border: "1px solid {colors.hairline-strong}"
    rounded: "{rounded.lg}"
    padding: "12px 16px"
  dialog:
    backgroundColor: "{colors.surface-glass}"
    border: "1px solid {colors.hairline-strong}"
    backdropFilter: "blur(16px)"
    rounded: "{rounded.xl}"
    padding: "24px"
---

## Overview

The AI Global OS dashboard is a **command center for sovereign AI engineering**. It is not a marketing surface; it is a dark, data-dense operational cockpit where personas, runtime state, budget, memory, skills, graphify, and telemetry are visible and actionable at a glance. The UI should feel like an advanced IDE crossed with a mission-control timeline: calm, precise, fast, and never deceptive.

**Key characteristics:**
- **Dark-first and always-on.** The canvas is near-black lapis charcoal (`{colors.canvas}`). Every light surface is an intentional inversion for focused tasks (e.g., a confirmation modal or public share page), never a default.
- **AI state is cyan.** The primary accent (`{colors.primary}` — `#22d3ee`) is reserved for the active AI state: current persona, running workflow, live memory query, graph highlight.
- **Knowledge is violet.** Memory, graphify, and skill references use the violet family (`{colors.accent-violet}` and `{colors.accent-violet-soft}`) to distinguish long-term context from live execution.
- **Policy is explicit.** Green (`{colors.accent-lime}`) means allowed/completed, amber means warning/budget at 80%, red means blocked/denied. No status is communicated only by color; every status pill has a text label.
- **Command palette as the front door.** `Cmd/Ctrl + K` opens a global command palette (`{components.command-palette}`). Users and agents can run workflows, switch personas, query memory, or open a skill without leaving the keyboard.
- **Bento grid metrics.** The home view is a grid of `{components.metric-card}` tiles: active sessions, tokens used today, memory hit rate, graphify nodes, pending skills, last audit.
- **Glassmorphism only where useful.** `{components.card-elevated}` and `{components.dialog}` use a saturated blur to float above dense data; cards inside data tables do not blur.

## Colors

### Brand & AI State
- **AI Cyan** (`{colors.primary}` `#22d3ee`): Live AI state, active workflow, current agent, focus ring, primary CTA.
- **Cyan Hover** (`{colors.primary-hover}` `#67e8f9`): Hover and selected states for primary actions.
- **Knowledge Violet** (`{colors.accent-violet}` `#8b5cf6`): Memory, graphify, skill graphs, cross-references.
- **Violet Soft** (`{colors.accent-violet-soft}`): Subtle violet background behind knowledge chips.

### Surface
- **Canvas** (`{colors.canvas}` `#0a0a0f`): Application background. Use for the main shell.
- **Surface 1** (`{colors.surface-1}` `#12131a`): Navigation rail, primary panels, card default.
- **Surface 2** (`{colors.surface-2}` `#181a22`): Metric cards, hover rows, code blocks, input backgrounds.
- **Surface 3** (`{colors.surface-3}` `#1e2029`): Active tab, selected row, pressed button.
- **Elevated Surface** (`{colors.surface-elevated}` `#252833`): Command palette, toasts, modals.
- **Glass Surface** (`{colors.surface-glass}`): Use with `backdrop-filter: blur(12px)` for floating chrome above scrollable content.

### Text
- **Ink** (`{colors.ink}` `#f7f8f8`): Primary text on dark.
- **Ink Muted** (`{colors.ink-muted}` `#9ca3af`): Secondary labels, timestamps, descriptions.
- **Ink Faint** (`{colors.ink-faint}` `#6b7280`): Tertiary metadata, disabled state.

### Hairline
- **Default** (`{colors.hairline}` `#2a2d38`): 1px borders on cards, separators, table row dividers.
- **Strong** (`{colors.hairline-strong}` `#3f4352`): Command palette borders, modal edges, focus emphasis.
- **Subtle** (`{colors.hairline-subtle}` `#1c1e25`): Extremely low-contrast dividers inside dense lists.

### Semantic
- **Lime / Success** (`{colors.accent-lime}`): Allowed, passing, complete, healthy.
- **Amber / Warning** (`{colors.accent-amber}`): Budget at 80%, degraded, ask mode, pending.
- **Red / Danger** (`{colors.accent-red}`): Blocked, denied, error, hard budget cap.

## Typography

### Font Family
- **UI / Display:** `Geist` with `Inter` fallback. Geist gives the dashboard a crisp, modern engineering voice. For Arabic text, fall back to `IBM Plex Sans Arabic / Noto Sans Arabic` with 1.5–1.7 line height.
- **Code / Logs:** `JetBrains Mono` with `Fira Code` fallback. Used for rules snippets, skill output, telemetry logs, CLI input.

### Hierarchy
| Token | Size | Weight | Use |
|---|---|---|---|
| `{typography.display-hero}` | 56px | 600 | Persona landing, empty-state hero |
| `{typography.display-lg}` | 40px | 600 | Section openers ("Memory", "Graphify") |
| `{typography.headline}` | 28px | 600 | Page title, e.g., "Runtime Kernel" |
| `{typography.card-title}` | 18px | 600 | Metric card titles, panel headings |
| `{typography.body}` | 14px | 400 | Default body, table cells, form labels |
| `{typography.caption}` | 12px | 500 | Status pills, timestamps, badges |
| `{typography.code}` | 13px | 400 | Rule snippet, log output, JSON preview |

## Spacing & Sizing

- **Dense by default.** Most internal padding is `{spacing.md}` or `{spacing.lg}`. `{spacing.xxl}` is the largest section gap.
- **Metric cards** use `{spacing.lg}` internal padding and `{spacing.md}` gaps in a CSS grid.
- **Nav rail** is 64px wide with `{spacing.sm}` icon-only buttons stacked vertically.
- **Command palette** is 640px max-width, centered, with generous `{spacing.xl}` input height.

## Components

### Command Palette
- Triggered by `Cmd/Ctrl + K` and the top-center search button.
- Input field uses `{colors.surface-2}` background, `{colors.primary}` focus ring.
- Sections: `Run workflow`, `Switch persona`, `Search memory`, `Query graphify`, `Open skill`.
- Each result has a command icon, a label in `{typography.body}`, and a hotkey hint in `{typography.caption}`.

### Metric Card
- Top row: `{components.metric-card-title}` + `{status-pill-*}`.
- Middle: the big number or sparkline in `{typography.display-lg}`.
- Bottom: micro copy in `{typography.caption}` and a trend delta (green arrow up, amber flat, red down).

### Status Pills
- Always include an icon and a text label. Never rely on color alone.
- Success: lime dot + label. Warning: amber dot + label. Danger: red dot + label.
- Violet pills denote knowledge/memory state; cyan pills denote active AI state.

### Code Block & Logs
- Code blocks use `{components.code-block}` with `font-variant-numeric: tabular-nums` for metrics.
- Log lines use `{components.log-line}` and alternate subtly by row, never by zebra striping.
- Syntax highlighting uses the existing color tokens (cyan for strings, violet for keywords, lime for success, red for errors).

### Navigation Rail
- Icon-only vertical bar on the far left.
- Active item uses `{colors.surface-3}` background and `{colors.primary}` left border.
- Tooltips appear on hover in `{components.toast}` style.

## Layout

### Global Shell
```
┌──────────────────────────────────────────────────────┐
│ Nav Rail │ Top Bar (command palette + persona chip)  │
│          │───────────────────────────────────────────│
│          │ Bento Grid of Metric Cards                │
│          │───────────────────────────────────────────│
│          │ Main Content (workflow / memory / graph)  │
└──────────────────────────────────────────────────────┘
```

- **Nav rail** is fixed 64px on the left.
- **Top bar** is 56px high, contains global search/palette, active persona chip, and budget indicator.
- **Content area** scrolls independently. The background is `{colors.canvas}`.

### Bento Grid
- Home and dashboard overviews use a 2/3/4 column CSS grid with `{spacing.md}` gap.
- Each cell is a `{components.metric-card}` or `{components.card-elevated}`.
- Avoid empty states: if a metric is zero, show a zero with a "Start a workflow" action, never a blank tile.

### Data Tables
- Row height 44px, `{typography.body}` size.
- Columns use tabular numerals for counts, budgets, and timestamps.
- Hover row = `{colors.surface-3}`. Selected row = `{colors.accent-violet-soft}`.

## Patterns

### Real-Time Indicators
- Pulsing cyan dot on the active workflow/persona avatar.
- Sparklines on metric cards use the same color as the metric (lime for success, amber for warning).
- Toast stack in the bottom-right corner for runtime events.

### Glassmorphism
- Use `{components.card-elevated}` for: command palette, modals, toasts, and floating side panels.
- Do not use blur inside scrollable tables or dense lists; it creates visual noise.

### Micro-interactions
- Transitions are fast: 150ms ease for hover, 200ms for expand/collapse.
- Heavy charts or large graphify canvases must defer rendering with `requestIdleCallback` / `IntersectionObserver`.
- Strict `aspect-ratio` on all media containers to prevent CLS.

### Focus & Accessibility
- Focus ring is a 2px `{colors.primary}` outline with 2px offset.
- All interactive elements must have a visible focus state; do not rely on browser defaults.
- Color-blind safe: every status indicator pairs an icon with a label.

## Tone of Voice

- **Concise and operational.** Labels are commands or facts, not marketing: "Ingest memory", not "Supercharge your memory".
- **Engineering confidence.** Use exact units: "271 tests passed", "92% coverage", "1.2M tokens".
- **No empty states.** A blank screen is a bug. Show a zero, a starter action, or a last-seen value.
- **Bilingual-ready.** Keep labels short because they will be mirrored to Arabic (`ar`) with longer average word length.

## Rules for AI Agents

1. **Dark-first.** The default shell is dark. Build dark components first; light surfaces are explicit inversions.
2. **Tokens win.** Use the YAML tokens above for color, type, spacing, and rounded. No ad-hoc hex values, no magic numbers.
3. **Status is explicit.** Every state change uses a labeled pill; every policy decision shows allow/deny and reason.
4. **Keyboard first.** Command palette, hotkeys, and focus order are first-class; mouse interactions are secondary.
5. **Dense, not cluttered.** Show more data per pixel, but group it into `{components.card}` and `{components.metric-card}` with clear hierarchy.
6. **Code is content.** Rule snippets, skill output, and telemetry logs are not decoration — they are core content and use `{typography.code}`.
7. **Respect motion.** Respect `prefers-reduced-motion`. Heavy animations must be off by default and opt-in.
8. **Mobile responsive, desktop primary.** Collapse nav rail to a bottom bar on <768px; keep command palette accessible via a floating trigger.
