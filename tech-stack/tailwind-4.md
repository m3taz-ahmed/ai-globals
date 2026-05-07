# Tailwind CSS v4 & Frontend UI

## 1. CSS ARCHITECTURE (OXIDE ENGINE)
- Tailwind v4 relies on CSS variables and a zero-config approach via `@theme`. Minimize the use of custom configuration files (`tailwind.config.js`) unless absolutely necessary.
- Utilize native CSS nesting combined with Tailwind utilities for complex component styling.

## 2. CLEAN HTML & UI COMPONENTS
- Extract highly repetitive utility classes into Blade components (or React/Vue components) rather than using `@apply` in CSS files.
- Ensure semantic HTML (e.g., `<button>` for actions, `<a>` for links, `<nav>`, `<aside>`).

## 3. RESPONSIVE & ACCESSIBILITY
- Mobile-first approach: write default utilities for mobile, then use `sm:`, `md:`, `lg:` for larger screens.
- Focus states (`focus:ring`, `focus:outline-none`) are mandatory for all interactive elements to ensure accessibility (A11y).