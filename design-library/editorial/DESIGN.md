# Editorial — Design System

A reading-first system for blogs, portfolios, and docs: serif display
type, warm paper tones, restrained chrome, print-inspired rhythm.
Original seed for aiZee.

## Colors

- `bg` `#FDFBF7` — warm paper
- `surface` `#F4F0E8` — pull quotes, code wells
- `border` `#DCD4C6` — rules and hairlines
- `text` `#1C1917` — ink
- `text-muted` `#78716C` — captions, metadata
- `accent` `#B45309` — amber ink for links and marks
- `selection` `#FDE68A` — highlighted text

Rules: links underlined on hover, accent on focus; imagery carries color —
the palette stays warm and quiet.

## Typography

- Display/body serif: `"Georgia", "Iowan Old Style", serif`
- UI/meta sans: `"Inter", "Segoe UI", sans-serif`
- Code: `"JetBrains Mono", Consolas, monospace`
- Scale: 13 / 15 / 17 / 22 / 28 / 36 / 48 (modular 1.33)
- Headings in serif; body measure 60–66ch; line-height 1.65
- Drop caps and small-caps allowed for article openers only

## Components

- Buttons: text links with underline; filled buttons rare, 4px radius
- Pull quotes: `surface` well, serif 22px, left accent rule 3px
- Figures: full-bleed allowed, caption in `text-muted` sans 13px
- Code blocks: `surface` bg, `border` frame, mono 13px
- Footnotes: superscript accent markers, end-note list in sans

## Layout

- Single-column measure column (640–720px) centered
- Wide figures may break to 1000px
- Spacing scale: 8 / 16 / 24 / 32 / 48 / 72 / 96
- Paragraph spacing 24px; section breaks use a 3-dot ornament
- Breakpoints: 720 / 1080

## Elevation

- Flat by principle — print metaphor
- Only transient UI (menus, toasts) gets `0 4px 16px rgba(28,25,23,0.12)`
- Sticky chrome casts a 1px `border` shadow, never a blur
