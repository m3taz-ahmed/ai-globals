# Midnight — Design System

A dark-first command-center system for dashboards and dense tooling:
deep backgrounds, glass surfaces, high-contrast text, neon accents.
Original seed for aiZee (the dashboard theme).

## Colors

- `bg` `#0B0F17` — page background (true dark, not grey)
- `surface` `#131A26` — panels, cards
- `surface-raised` `#1B2434` — hover/active surfaces
- `border` `#26314A` — low-contrast hairlines
- `text` `#E6EBF4` — primary text
- `text-muted` `#8B97AD` — secondary text
- `accent` `#6C63FF` — primary actions, focus rings
- `info` `#38BDF8` · `success` `#34D399` · `warn` `#FBBF24` · `danger` `#F87171`

Rules: accent reserved for the single primary action per view; semantic
colors for status only; WCAG AA contrast (4.5:1) for all text.

## Typography

- Family: `"Inter", "Segoe UI", Roboto, sans-serif`; mono `"JetBrains Mono", Consolas`
- Scale: 11 / 13 / 14 / 16 / 20 / 26 / 34
- Weights: 400 body, 500 labels, 700 headings
- Numbers in metrics/mono use tabular figures

## Components

- Buttons: 8px radius; primary = accent, secondary = `surface-raised` + border
- Cards: `surface` bg, `border` hairline, 12px radius, 20px padding
- Pills/badges: rounded-full, tinted bg at 12% alpha + full-alpha text
- Inputs: `surface` bg, `border` ring, focus = accent ring 2px
- Modals: `surface-raised` + backdrop `bg` at 70% alpha

## Layout

- Grid: 12-col fluid, 20px gutters, bento-card composition encouraged
- Spacing scale: 4 / 8 / 12 / 16 / 20 / 28 / 40 / 56
- Sidebar 240px fixed; content max-width 1440px
- Density: compact-first (13–14px body in tooling surfaces)

## Elevation

- Level 1: `0 2px 8px rgba(0,0,0,0.35)` — cards at rest
- Level 2: `0 8px 24px rgba(0,0,0,0.45)` — popovers, dropdowns
- Level 3: `0 16px 48px rgba(0,0,0,0.55)` — modals
- Inner glow `inset 0 1px 0 rgba(255,255,255,0.04)` on raised surfaces
