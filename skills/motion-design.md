---
name: motion-design
description: Motion Design Auditor — animation quality from 3 designer perspectives with severity-ranked findings.
---
[SKILL] motion-design
[OBJ] Audit and elevate UI motion design for purpose, choreography, and accessibility across 3 expert perspectives.
[RULES]
1. [REQ] Emil Kowalski Perspective — Subtle & Purposeful:
   - Animations must be subtle, not flashy — the user should feel them, not notice them.
   - Use spring physics over linear easing for a natural, organic feel.
   - Motion should guide attention, not demand it.
   - Prefer opacity and transform over layout properties (width, top, margin).
   - Duration should feel instant — if the user notices the duration, it is too long.
   - Every transition must have a clear cause: state change, user action, or data load.

2. [REQ] Jakub Krehel Perspective — Choreography & Stagger:
   - Entrance animations should choreograph elements in sequence, not all at once.
   - Stagger items 50-100ms apart, maximum 5 items staggered — beyond that, animate as a group.
   - Define clear entrance (fade-up, scale-in) and exit (fade-down, scale-out) patterns.
   - Exit animations should be faster than entrance — users want dismissal to feel snappy.
   - Coordinate parent-child relationships — child animates after parent settles.

3. [REQ] Jhey Tompkins Perspective — Delight & Surprise:
   - Inject micro-interactions that reward engagement (button press, toggle spring, hover lift).
   - Use surprise sparingly — unexpected animation on first interaction creates delight; on every interaction it becomes noise.
   - Add easter-egg-level detail for power users (konami code, long-press reveals).
   - Interactive elements should respond within 100ms to feel immediate.
   - Delight must never block or delay the user's primary task.

4. [REQ] Timing Checklist:
   - UI element transitions: 200-400ms.
   - Page / section transitions: 400-600ms.
   - Micro-interactions: 100-200ms.
   - Loading states: 300ms minimum delay before showing spinner (avoid flash).
   - Exit animations: 30-50% faster than entrance.
   - Stagger interval: 50-100ms, max 5 items staggered individually.

5. [REQ] Easing Checklist:
   - Entrance transitions: ease-out (fast start, slow end — element arrives gently).
   - Exit transitions: ease-in (slow start, fast exit — element leaves decisively).
   - Interactive / feedback animations: spring physics (natural overshoot and settle).
   - Avoid linear easing except for continuous loops (spinners, progress bars).
   - Avoid ease-in-out for UI transitions — it feels sluggish at both ends.

6. [REQ] Choreography Checklist:
   - Stagger interval 50-100ms between items.
   - Maximum 5 items staggered individually — group the rest.
   - Parent animates before children.
   - No more than 2 simultaneous animation layers (e.g., background + foreground).
   - Coordinate shared-element transitions (list item to detail view) — match position and scale.

7. [REQ] Purpose Checklist:
   - Every animation must serve a function: spatial orientation, feedback, status change, or attention guidance.
   - If removing the animation does not degrade UX, it is decorative and must be opt-in.
   - No animation on static informational content.
   - Loading animations must reflect actual progress when available, not fake motion.

8. [REQ] Accessibility Checklist:
   - Respect prefers-reduced-motion: reduce — disable or replace non-essential animations with instant transitions.
   - No vestibular triggers — avoid large-scale parallax, rapid zoom, horizontal auto-scroll, full-screen rotation.
   - No content flashing more than 3 times per second.
   - Auto-playing animation longer than 5s must have pause, stop, or hide control.
   - Reduced-motion fallback must convey the same information (instant state change instead of animated).

9. [REQ] Severity Rankings:
   - CRITICAL: Vestibular triggers (parallax, rapid zoom, auto-scroll) with no reduced-motion fallback.
   - HIGH: Janky animation (fps drops below 50) or animation with no functional purpose that blocks interaction.
   - MEDIUM: Wrong timing (too slow >600ms for UI, too fast <100ms for page), wrong easing direction.
   - LOW: Polish issues — inconsistent stagger, missing spring physics, decorative animation without opt-in.

[CMD] GSAP: `npm i gsap`
- Use `gsap.context()` for scoping animations to a component.
- Use `gsap.timeline()` for choreography and staggered sequences.
- Use `ScrollTrigger` plugin for scroll-driven motion.
- Use `gsap.matchMedia()` for reduced-motion and responsive handling.
- Docs: Context7 `/gsap/gsap`.

[CMD] Framer Motion: `npm i framer-motion`
- Use `<motion.div>` with `animate` / `exit` props for declarative animation.
- Use `AnimatePresence` for exit animations on unmount.
- Use `layout` prop for shared-element transitions.
- Use `useReducedMotion()` hook for accessibility-aware animation.
- Docs: Context7 `/framer/motion`.

[CMD] CSS Animations:
- Prefer `@keyframes` + `animation` for simple loops; `transition` for state changes.
- Use `transform` and `opacity` only (compositor-friendly, no layout thrash).
- Query `@media (prefers-reduced-motion: reduce)` to disable or simplify.
- Avoid animating `width`, `height`, `top`, `left`, `margin`, `padding` (cause layout reflow).
