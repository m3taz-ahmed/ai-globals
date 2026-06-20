# GSAP Core Patterns Reference

## Essential API

### Basic Tweens

```tsx
// Animate FROM initial state TO current CSS state
gsap.from(".element", {
  opacity: 0,
  y: 50,
  duration: 0.8,
  ease: "power2.out",
});

// Animate TO target state from current
gsap.to(".element", {
  x: 100,
  rotation: 360,
  duration: 1,
  ease: "power3.inOut",
});

// Animate FROM start TO end (explicit both)
gsap.fromTo(".element",
  { opacity: 0, y: 30 },    // from
  { opacity: 1, y: 0, duration: 0.6 }  // to
);

// Instant set (no animation)
gsap.set(".element", { opacity: 0, y: 50 });
```

### Timelines (ALWAYS use for sequences)

```tsx
const tl = gsap.timeline({
  defaults: { duration: 0.6, ease: "power2.out" }
});

tl.from(".hero-title", { opacity: 0, y: 40 })
  .from(".hero-subtitle", { opacity: 0, y: 30 }, "-=0.3")  // overlap by 0.3s
  .from(".hero-cta", { opacity: 0, scale: 0.8, ease: "back.out(1.7)" }, "-=0.2")
  .from(".hero-badge", { opacity: 0, x: -20 }, "<");  // same start as previous

// Position parameters:
// "-=0.3"  → 0.3s before previous ends (overlap)
// "+=0.5"  → 0.5s after previous ends (gap)
// "<"      → same start time as previous tween
// "<0.2"   → 0.2s after previous starts
// 2        → absolute 2s from timeline start
```

### Stagger (for multiple elements)

```tsx
gsap.from(".card", {
  opacity: 0,
  y: 40,
  duration: 0.5,
  stagger: 0.1,           // 0.1s between each
  ease: "power2.out",
});

// Advanced stagger
gsap.from(".grid-item", {
  opacity: 0,
  scale: 0.8,
  stagger: {
    amount: 0.8,           // total stagger time spread
    grid: [4, 3],          // 4 rows, 3 cols
    from: "center",        // "start", "center", "end", "edges", "random"
    ease: "power2.inOut",
  }
});
```

## Easing Quick Reference

| Category | Ease Name | Character | Best For |
|----------|-----------|-----------|----------|
| **Smooth** | `power1.out` | Gentle decelerate | Subtle fades, text reveals |
| **Standard** | `power2.out` | Natural decelerate | Cards entering, most UI motion |
| **Punchy** | `power3.out` | Quick start, smooth end | Hero reveals, important elements |
| **Dramatic** | `power4.out` | Very fast start | Dramatic entrances, cinematic |
| **Bounce** | `back.out(1.7)` | Overshoots then settles | CTAs, badges, playful elements |
| **Elastic** | `elastic.out(1, 0.3)` | Spring wobble | Attention-grabbers, fun UI |
| **Smooth both** | `power2.inOut` | Smooth start and end | Section transitions, morphs |
| **Linear** | `none` | Constant speed | Progress bars, loading indicators |
| **Custom** | `"expo.out"` | Exponential decelerate | Premium, Apple-style motion |

**Rule of thumb:** Use `.out` easing 90% of the time (elements arriving). Use `.inOut` for transitions between states. Rarely use `.in` alone.

## React Integration with useGSAP

```tsx
"use client";
import { useRef } from "react";
import { gsap } from "gsap";
import { useGSAP } from "@gsap/react";
import { ScrollTrigger } from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);

function AnimatedSection() {
  const containerRef = useRef<HTMLDivElement>(null);

  useGSAP(() => {
    // All GSAP code here — auto-cleaned on unmount
    const tl = gsap.timeline({
      scrollTrigger: {
        trigger: containerRef.current,
        start: "top 80%",
        toggleActions: "play none none none",
      }
    });

    tl.from(".section-title", { opacity: 0, y: 30, duration: 0.6 })
      .from(".section-card", { opacity: 0, y: 20, stagger: 0.1 }, "-=0.3");

  }, { scope: containerRef }); // scope limits queries to this container

  return (
    <div ref={containerRef}>
      <h2 className="section-title">Title</h2>
      <div className="section-card">Card 1</div>
      <div className="section-card">Card 2</div>
    </div>
  );
}
```

### useGSAP with Dependencies

```tsx
useGSAP(() => {
  if (!data) return; // guard for async data
  
  gsap.from(".item", {
    opacity: 0,
    y: 20,
    stagger: 0.08,
    scrollTrigger: { trigger: ".items-grid", start: "top 80%" }
  });
}, { scope: containerRef, dependencies: [data] });
```

## gsap.quickTo() — For Mouse-Follow Effects

```tsx
useGSAP(() => {
  const xTo = gsap.quickTo(".cursor", "x", { duration: 0.4, ease: "power3" });
  const yTo = gsap.quickTo(".cursor", "y", { duration: 0.4, ease: "power3" });

  window.addEventListener("mousemove", (e) => {
    xTo(e.clientX);
    yTo(e.clientY);
  });
}, { scope: containerRef });
```

## gsap.matchMedia() — Responsive Animations

```tsx
useGSAP(() => {
  const mm = gsap.matchMedia();

  mm.add("(min-width: 768px)", () => {
    // Desktop animations — full parallax, complex staggers
    gsap.from(".hero-image", {
      scale: 1.2,
      scrollTrigger: { trigger: ".hero", scrub: 1 }
    });
  });

  mm.add("(max-width: 767px)", () => {
    // Mobile — simplified, no parallax
    gsap.from(".hero-image", { opacity: 0, duration: 0.6 });
  });

  mm.add("(prefers-reduced-motion: reduce)", () => {
    // Reduced motion — instant states, no animation
    gsap.set(".animated", { clearProps: "all" });
  });
}, { scope: containerRef });
```

## gsap.context() — Vanilla JS Cleanup

```ts
// For non-React projects
const ctx = gsap.context(() => {
  gsap.from(".title", { opacity: 0, y: 30 });
  gsap.from(".card", { opacity: 0, stagger: 0.1 });
}, "#my-section"); // scope selector

// Cleanup later
ctx.revert(); // kills all animations created inside
```

## Utility Methods

```tsx
// Snap to grid values
gsap.utils.snap(10)(47);        // → 50

// Map a range to another
gsap.utils.mapRange(0, 100, 0, 1, 50);  // → 0.5

// Clamp values
gsap.utils.clamp(0, 100, 150);  // → 100

// Wrap around (for infinite carousels)
gsap.utils.wrap([0, 1, 2, 3], 5);  // → 1

// Convert NodeList to array
const cards = gsap.utils.toArray(".card");

// Random
gsap.utils.random(1, 10);       // random between 1-10
gsap.utils.random([1, 5, 10]);  // random from array
```

## Initial CSS States (Prevent FOUC)

Always set initial states in CSS for animated elements:

```css
/* Elements that will animate in */
.animate-in {
  opacity: 0;
  transform: translateY(30px);
}

/* Only when JS is available */
.js-loaded .animate-in {
  /* GSAP will handle from here */
}

/* Reduced motion: show everything immediately */
@media (prefers-reduced-motion: reduce) {
  .animate-in {
    opacity: 1 !important;
    transform: none !important;
  }
}
```

## Timeline Control

```tsx
const tl = gsap.timeline({ paused: true });

tl.to(".menu", { x: 300 })
  .to(".overlay", { opacity: 1 }, "<");

// Control
tl.play();
tl.reverse();
tl.pause();
tl.restart();
tl.progress(0.5);  // jump to 50%
tl.timeScale(2);   // 2x speed
```