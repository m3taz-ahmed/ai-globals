# Responsive & Mobile-First UI Standards

## 1. ADAPTIVE LAYOUTS
- **Mobile-First:** Always design for `base` (mobile) first, then scale to `md`, `lg`, and `xl`.
- **Container Queries:** Favor `@container` over `@media` for component-level responsiveness. Use Tailwind's `@tailwindcss/container-queries` plugin.
- **Fluid Typography:** Use `clamp()` for font sizes to ensure smooth scaling between screen sizes.

## 2. NATIVE-LIKE MOBILE UX
- **Touch Targets:** Ensure buttons and links are at least `44px x 44px`.
- **Gestures:** Implement swipe-to-dismiss or pull-to-refresh where applicable using `Alpine.js` or `Framer Motion`.
- **Safe Areas:** Use `env(safe-area-inset-*)` for devices with notches.
- **App-like Navigation:** On mobile, prefer bottom navigation bars or full-screen overlay menus.

## 3. LAYOUT MIRRORING (RTL/LTR)
- **Logical Properties:** Use `ms-*` (margin-start) and `pe-*` (padding-end) instead of `ml-*` and `pr-*`.
- **Flexbox/Grid:** Rely on `flex-row` and `grid-cols` which automatically respect the `dir` attribute.
- **Icons:** Flip directional icons (arrows, chevrons) in RTL mode using `rtl:-scale-x-100`.
