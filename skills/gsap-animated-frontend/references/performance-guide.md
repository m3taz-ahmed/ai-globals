# Performance & Accessibility Guide

## GPU-Friendly Animation Properties

### ALWAYS animate (composited — GPU-accelerated):
- `x`, `y` (translateX/Y)
- `scale`, `scaleX`, `scaleY`
- `rotation`, `rotateX`, `rotateY`
- `opacity`

### NEVER animate (triggers layout reflow):
- `width`, `height`
- `top`, `left`, `right`, `bottom`
- `margin`, `padding`
- `border-width`, `font-size`
- `line-height`

### Use cautiously:
- `clip-path` — GPU on some browsers, not all
- `filter` (blur, brightness) — can be expensive
- `box-shadow` — avoid animating, use `opacity` on a pseudo-element with static shadow instead
- `background-color` — OK for small elements, avoid on large surfaces

## will-change Strategy

```css
/* Only add to elements that WILL animate soon */
.will-animate-on-hover:hover {
  will-change: transform, opacity;
}

/* Remove after animation — don't leave will-change permanently */
```

GSAP adds `will-change` automatically during animations. Don't add it globally.

## ScrollTrigger Performance

### Use `ScrollTrigger.batch()` for grids
```tsx
// BAD — 50 individual ScrollTriggers
cards.forEach(card => {
  gsap.from(card, { scrollTrigger: { trigger: card } });
});

// GOOD — 1 ScrollTrigger, batched
ScrollTrigger.batch(".card", {
  onEnter: (batch) => gsap.from(batch, { opacity: 0, stagger: 0.05 }),
});
```

### Limit active ScrollTriggers
- Aim for < 20 active ScrollTriggers per page
- Use `once: true` for elements that only need to animate once
- Kill ScrollTriggers for off-screen sections in SPAs

### Scrub performance
- `scrub: true` (instant) is cheapest
- `scrub: 1` (1s smooth) is standard — good balance
- Higher scrub values = more interpolation frames = slightly more CPU

## Mobile Optimization

### Disable heavy animations on mobile
```tsx
gsap.matchMedia().add("(max-width: 767px)", () => {
  // Simple fades only — no parallax, no pinning, no scrub
  gsap.from(".content", { opacity: 0, duration: 0.5 });
});

gsap.matchMedia().add("(min-width: 768px)", () => {
  // Full desktop animations
});
```

### Mobile-specific rules:
1. **No parallax on touch** — janky with touch scrolling
2. **No pinned sections** — confuses touch scroll behavior
3. **Reduce stagger counts** — fewer items visible = less stagger needed
4. **Shorter durations** — mobile users are impatient
5. **No custom cursor** — no cursor on touch devices
6. **Avoid `scrub`** — touch scroll momentum makes scrub feel laggy

## Accessibility — prefers-reduced-motion

### ALWAYS implement this:

```tsx
useGSAP(() => {
  const mm = gsap.matchMedia();

  mm.add("(prefers-reduced-motion: reduce)", () => {
    // Instantly show all content — no animation
    gsap.set(".animated", { clearProps: "all" });
    // Kill all ScrollTriggers
    ScrollTrigger.getAll().forEach(t => t.kill());
  });

  mm.add("(prefers-reduced-motion: no-preference)", () => {
    // Normal animations here
  });
});
```

### CSS fallback:
```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }

  .animate-in {
    opacity: 1 !important;
    transform: none !important;
  }
}
```

## Preventing FOUC (Flash of Unstyled Content)

### CSS initial states for animated elements:
```css
/* Set initial hidden states in CSS (before JS loads) */
.fade-in { opacity: 0; }
.slide-up { opacity: 0; transform: translateY(30px); }
.scale-in { opacity: 0; transform: scale(0.9); }

/* Show immediately if reduced motion */
@media (prefers-reduced-motion: reduce) {
  .fade-in, .slide-up, .scale-in {
    opacity: 1 !important;
    transform: none !important;
  }
}

/* Fallback: show if JS fails to load after 3s */
@supports (animation-timeline: scroll()) {
  /* Progressive enhancement */
}
```

### React: Handle hydration
```tsx
// Add class after hydration to enable animations
useEffect(() => {
  document.documentElement.classList.add("js-ready");
}, []);

// CSS: only hide elements when JS is ready
// .js-ready .fade-in { opacity: 0; }
```

## Loading Strategy

### Above the fold: Animate on page load
```tsx
useGSAP(() => {
  // No ScrollTrigger — runs immediately
  gsap.from(".hero-title", { opacity: 0, y: 40, duration: 0.8 });
});
```

### Below the fold: Animate on scroll
```tsx
useGSAP(() => {
  gsap.from(".section", {
    opacity: 0,
    y: 30,
    scrollTrigger: { trigger: ".section", start: "top 80%" }
  });
});
```

### Lazy-load heavy animations
```tsx
// Only init heavy animation sections when they're close to viewport
ScrollTrigger.create({
  trigger: ".heavy-section",
  start: "top 200%",  // 2 viewports away
  once: true,
  onEnter: () => initHeavyAnimations(),
});
```

## Bundle Size

| Package | Size (minified + gzip) |
|---------|----------------------|
| gsap core | ~24 KB |
| ScrollTrigger | ~10 KB |
| @gsap/react | ~2 KB |
| Lenis | ~5 KB |
| **Total typical** | **~41 KB** |

### Tree-shake unused plugins:
```tsx
// Only import what you use
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
// Don't import Draggable, Flip, etc. if not using them
```

## Performance Checklist

- [ ] Only animate `transform` and `opacity`
- [ ] Use `ScrollTrigger.batch()` for repeated elements
- [ ] < 20 active ScrollTriggers per page
- [ ] Mobile: no parallax, no pinning, simplified animations
- [ ] `prefers-reduced-motion` respected
- [ ] CSS initial states prevent FOUC
- [ ] Above-fold animates on load, below-fold on scroll
- [ ] Unused GSAP plugins not imported
- [ ] `ScrollTrigger.refresh()` called after dynamic content
- [ ] Animations cleaned up on component unmount