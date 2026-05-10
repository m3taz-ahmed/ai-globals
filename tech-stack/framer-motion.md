# Tech-Stack: Framer Motion

> [!NOTE]
> **TRIGGER:** LOAD ON frontend animations, complex transitions, interactive UI elements.
> **SCOPE:** Framer Motion, React, Next.js.

## 1. Animation Patterns
- Use the `AnimatePresence` component to handle exit animations for unmounting components.
- Define `variants` for complex orchestrated animations, keeping the JSX clean and reusable.
- Implement layout animations (`layout` prop) for smooth transitions when DOM structures change (e.g., list reordering).
- Use shared layout animations (`layoutId`) to morph elements smoothly between different components or routes.

## 2. Performance & Accessibility
- Leverage GPU acceleration by animating `transform` and `opacity` properties instead of layout properties (width, top, left).
- Use the `will-change` CSS property cautiously for complex animations to hint the browser.
- ALWAYS respect the user's motion preferences by using the `useReducedMotion` hook or the `prefers-reduced-motion` media query to disable heavy animations.

## 3. Interaction
- Use gesture animations (`whileHover`, `whileTap`, `whileDrag`) for immediate visual feedback.
- Implement scroll-triggered animations (`whileInView`) for landing page reveals.

## 4. Hard Constraints
- NEVER animate layout-triggering properties (like `height` or `margin`) continuously, as it causes browser reflows and jank.
- NEVER ignore the `useReducedMotion` preference for non-essential animations.
- ALWAYS ensure animations have a distinct purpose and don't overwhelm the user interface.

---

## ✅ FRAMER MOTION COMPLIANCE CHECK (Mandatory)
- [ ] **Performance:** Are only `transform` and `opacity` properties animated continuously?
- [ ] **Accessibility:** Is the `useReducedMotion` hook implemented for heavy animations?
- [ ] **Architecture:** Are `variants` used to keep JSX uncluttered?
