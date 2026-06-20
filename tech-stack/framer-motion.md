[TECH] framer-motion
[OBJ] Framer Motion Standards (v11+).
[RULES]
1. [REQ] Components: Use `motion` (not `m`). `AnimatePresence` for unmounting. `layoutId` for shared layout.
2. [REQ] Performance: Animate `transform` and `opacity` only (GPU accelerated). Use `LazyMotion`.
3. [REQ] A11y: Respect `useReducedMotion` hook always.
4. [PROHIBIT] SSR: NEVER import in Server Components. Use `"use client"` directive.
