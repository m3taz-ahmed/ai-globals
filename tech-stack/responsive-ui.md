[TECH] responsive-ui
[OBJ] Responsive & Mobile-First UI Standards.
[RULES]
1. [REQ] Adaptive: Mobile-First (`base` -> `md`/`lg`). Container Queries (`@container`) > `@media`. Fluid Typography (`clamp()`).
2. [REQ] UX: Touch targets min 44x44px. Gestures via Alpine/Framer. Safe areas (`env(safe-area-inset-*)`). Bottom nav for mobile.
3. [REQ] RTL/LTR: Logical properties (`ms-*`, `pe-*`). Flip directional icons (`rtl:-scale-x-100`).
