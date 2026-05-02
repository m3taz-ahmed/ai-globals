# Modern Frontend & UI Standards
- **Framework:** Tailwind CSS 4.0+.
- **Configuration:** Use CSS-first configuration (`@theme` blocks in CSS) instead of JS-based `tailwind.config.js` where possible.
- **Component Design:** Favor atomic component structures. Every UI element must be reusable and self-contained.

## 1. ACCESSIBILITY (A11Y)
- **Contrast:** Maintain WCAG AA compliance for all text and interactive elements.
- **ARIA:** Use appropriate ARIA labels and roles for dynamic components (modals, dropdowns).
- **Keyboard Navigation:** Every interactive element MUST be accessible via keyboard (proper `tabindex` and focus states).

## 2. PERFORMANCE
- **Asset Optimization:** Use Vite's modern bundling features. Prefer SVG over icon fonts.
- **Lazy Loading:** Images and heavy UI components should be lazy-loaded by default.

## 3. DESIGN SYSTEM
- **Consistency:** Use a centralized token system (Colors, Spacing, Typography) defined in the global CSS theme.
- **Dark Mode:** Support high-contrast dark mode natively using the `dark:` utility.

## 4. ANIMATIONS & INTERACTIONS
- **Micro-animations:** Use `Tailwind` transitions for simple hovers (`transition-all duration-300`).
- **Complex Orchestration:** Use `Framer Motion` (React) or `GSAP` (Vanilla/Blade) for entry animations, scroll-triggered reveals, and complex UI sequencing.
- **Performance:** Ensure animations use `transform` and `opacity` to keep them on the GPU (60fps mandate).
- **Reduced Motion:** Always respect `prefers-reduced-motion` media queries.

