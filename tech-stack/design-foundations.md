[TECH] design-foundations
[OBJ] Global Design Foundations.
[RULES]
1. [REQ] Layouts: Bento Grids (`gap-4`, `aspect-ratio`). Glassmorphism (`backdrop-blur`, fallback BG). Neumorphism for subtle controls. Mesh gradients.
2. [REQ] Wow Factor: Micro-interactions on every element. Bold typography. NO empty states. High contrast/saturated Dark Mode (use zinc/slate).
3. [REQ] Typography: English (Inter/Outfit/Geist). Arabic (IBM Plex/Readex Pro/Noto Sans, 1.5-1.7 line-height).
4. [REQ] Performance: Heavy animations MUST use `requestIdleCallback`/`IntersectionObserver`. Prevent CLS via strict `aspect-ratio` on containers.
