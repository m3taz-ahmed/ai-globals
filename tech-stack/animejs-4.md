[TECH] animejs-4
[OBJ] Anime.js v4 — all-in-one JS animation engine (~24.5KB full, modular). Alternative to GSAP (lighter) and Framer Motion (framework-free). Verified against animejs.com docs via Context7 `/websites/animejs` (v4.2.2/4.3.0).
[RULES]
1. [REQ] Install: `npm i animejs` — v4 API only (`import { animate } from 'animejs'`). v3 API (`anime({targets:...})`) is legacy — never mix.
2. [REQ] Modular imports: pay per module — `import { animate, stagger, spring, createTimeline, createDraggable, createScope, createSpring, onScroll, morphTo, createDrawable, createMotionPath, utils, waapi } from 'animejs'`; utils also at `'animejs/utils'`. Bundle: Timer 5.6KB core; add Draggable +6.4K, Scroll +4.3K, WAAPI +3.5K only when used.
3. [REQ] Core: `animate(targets, params)` — targets = selector string, element, JS object, or array. Per-property params, function-based values, keyframes arrays, `composition: 'blend'` for additive transforms.
4. [REQ] Timeline: `createTimeline().add(target, params, position)` — position `'<'` (with prev), `'+=x'` offsets, `stagger()` as position for grid cascades.
5. [REQ] Stagger: `stagger(ms, { grid:[r,c], from:'center'|'first'|'last'|[x,y] })` — time/values/timeline-position modes.
6. [REQ] Scroll: `autoplay: onScroll({ sync: true })` ties animation to scroll; thresholds/callbacks on the Scroll Observer.
7. [REQ] SVG: `morphTo(target)` shape morphing, `createDrawable('path')` + `draw: '0 1'` line drawing, `createMotionPath('.path')` motion along path.
8. [REQ] Draggable + springs: `createDraggable(el, { container:[t,r,b,l], releaseEase: spring({ bounce }) })`; `spring({ stiffness, damping })` or `spring({ bounce })`.
9. [REQ] Scope: `createScope({ mediaQueries, root })` + `.add(({ matches }) => ...)` — media-query-reactive animations with auto cleanup. Always include `(prefers-reduced-motion)` and skip/trivial-ize motion when matched `[A11y-005]`.
10. [REQ] WAAPI: `waapi.animate()` exports to Web Animations API for off-main-thread playback.
11. [PROHIBIT] No `anime({...})` v3 signature. No layout-thrash properties (width/height/top/left) when transform equivalents exist — prefer `x/y/scale/rotate` + opacity (60fps, composited).
12. [REQ] Cleanup: return/keep `.revert()` on scopes and timelines in component teardown — prevents leaks in SPA mounts.
13. [CMD] Easings: built-ins `inOut`, `inOutExpo`, `inOut(3)` power curve; `spring()` for physics; `steps(n)` for discrete. Visual editor: animejs.com/easing-editor.
