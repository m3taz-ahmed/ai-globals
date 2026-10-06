# Minimal — Design System

A stripped-back, content-first system: near-monochrome palette, generous
whitespace, single accent color, zero decoration. Original seed for aiZee.

## Colors

- `bg` `#FFFFFF` — page background
- `surface` `#FAFAFA` — cards, wells
- `border` `#E5E5E5` — hairline dividers
- `text` `#111111` — primary text
- `text-muted` `#6B6B6B` — secondary text
- `accent` `#2563EB` — single accent (links, primary buttons)
- `danger` `#DC2626` · `success` `#16A34A`

Rules: one accent only; no gradients; color must never be the only signal.

## Typography

- Family: system stack `-apple-system, "Segoe UI", Roboto, sans-serif`
- Scale: 12 / 14 / 16 / 20 / 24 / 32 / 40 (1.25 ratio)
- Weights: 400 body, 600 headings, 500 emphasis — no light weights
- Line-height: 1.5 body, 1.2 headings; max measure 68ch

## Components

- Buttons: 6px radius, 1px border; primary = accent fill, secondary = ghost
- Cards: `surface` bg, `border` hairline, 16px padding, 8px radius
- Inputs: 40px height, `border` ring, focus = accent ring 2px
- Tables: hairline row separators only, no vertical rules

## Layout

- Grid: 12-col, 24px gutters, max-width 1120px
- Spacing scale: 4 / 8 / 12 / 16 / 24 / 32 / 48 / 64
- Breakpoints: 640 / 768 / 1024 / 1280
- Sections separated by whitespace (64px), not rules

## Elevation

- Level 0: flat (default) — everything sits on the page
- Level 1: `0 1px 2px rgba(0,0,0,0.06)` — popovers, dropdowns only
- No elevation above level 1; use borders, not shadows, to group
