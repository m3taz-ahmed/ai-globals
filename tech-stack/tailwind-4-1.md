# Tailwind CSS v4.1 Standards

## 1. ENGINE
- **Oxide (Rust-Based):** Utilizes the oxidized Rust-based engine implicitly. Build times are significantly faster than v3. No configuration needed.

## 2. CSS-FIRST CONFIGURATION
- **@theme:** Use `@theme` blocks in CSS for all design tokens (colors, spacing, fonts). Avoid `tailwind.config.js` unless required for plugins.
- **Nesting:** Use advanced native CSS nesting seamlessly. Avoid complex `@apply` chains; use standard utility classes in HTML.
- **CSS Variables:** All design tokens are exposed as CSS custom properties. Use `var(--color-primary)` in custom CSS when needed.

## 3. MODERN LAYOUT
- **Container Queries:** Use `@container` queries for component-level responsive design (not just viewport-based).
- **@starting-style:** Use `@starting-style` for entry animations on elements transitioning from `display: none`.
- **Subgrid:** Leverage CSS Subgrid for aligning nested grid items to parent grid tracks.

## 4. ANIMATIONS & TRANSITIONS
- **Built-In:** Use Tailwind's `animate-*` utilities for common animations. Define custom keyframes in `@theme`.
- **View Transitions:** Support the View Transitions API for page-level transitions in SPAs.
- **Reduced Motion:** Always include `motion-reduce:` variants for accessibility on animated elements.

## 5. COMPATIBILITY
- **v3 Migration:** Not all v3 utilities are 1:1 compatible. Refer to the official migration guide for renamed/removed utilities.
- **PostCSS:** Tailwind v4 includes its own CSS processing. PostCSS is optional, not required.