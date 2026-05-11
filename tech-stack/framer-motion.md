# Tech-Stack: Framer Motion

> [!NOTE]
> **TRIGGER:** LOAD ON frontend animations, complex transitions, interactive UI elements.
> **SCOPE:** Framer Motion v11+, `motion` component, React 19, Next.js.

## 1. Animation Patterns
- Use the `motion` component (replaces the legacy `m` component in v11+). The `motion` component is the default and is fully optimized for React 19 and Server Components.
- Use the `AnimatePresence` component to handle exit animations for unmounting components.
- Define `variants` for complex orchestrated animations, keeping the JSX clean and reusable.
- Implement layout animations (`layout` prop) for smooth transitions when DOM structures change (e.g., list reordering).
- Use shared layout animations (`layoutId`) to morph elements smoothly between different components or routes.

## 2. Performance & Accessibility
- Leverage GPU acceleration by animating `transform` and `opacity` properties instead of layout properties (width, top, left).
- Use the `will-change` CSS property cautiously for complex animations to hint the browser.
- ALWAYS respect the user's motion preferences by using the `useReducedMotion` hook or the `prefers-reduced-motion` media query to disable heavy animations.
- For server-rendered content, use the `LazyMotion` wrapper with `domAnimation` feature bundle to reduce initial JS payload by only loading required animation features.

## 3. Interaction
- Use gesture animations (`whileHover`, `whileTap`, `whileDrag`) for immediate visual feedback.
- Implement scroll-triggered animations (`whileInView`) for landing page reveals.

## 4. Next.js Integration
- Import `motion` from `framer-motion/client` in Client Components only — Framer Motion is inherently client-side.
- Use `"use client"` directive on any component file that imports from `framer-motion`.
- For Server Components with animations, wrap only the animated portion in a Client Component boundary.

## 5. Hard Constraints
- NEVER animate layout-triggering properties (like `height` or `margin`) continuously, as it causes browser reflows and jank.
- NEVER ignore the `useReducedMotion` preference for non-essential animations.
- ALWAYS ensure animations have a distinct purpose and don't overwhelm the user interface.
- NEVER import from `framer-motion` in Server Components; always isolate in Client Components.

---

## ✅ FRAMER MOTION COMPLIANCE CHECK (Mandatory)
- [ ] **Performance:** Are only `transform` and `opacity` properties animated continuously?
- [ ] **Accessibility:** Is the `useReducedMotion` hook implemented for heavy animations?
- [ ] **Architecture:** Are `variants` used to keep JSX uncluttered?
- [ ] **SSR Safety:** Are Framer Motion imports isolated to Client Components only?
