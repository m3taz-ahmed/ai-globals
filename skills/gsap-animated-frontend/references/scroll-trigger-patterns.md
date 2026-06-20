# ScrollTrigger Patterns Reference

## Basic Setup

```tsx
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
gsap.registerPlugin(ScrollTrigger);
```

## Pattern 1: Reveal on Scroll (Most Common)

```tsx
gsap.from(".section-content", {
  opacity: 0,
  y: 50,
  duration: 0.8,
  ease: "power2.out",
  scrollTrigger: {
    trigger: ".section-content",
    start: "top 80%",      // trigger top hits 80% viewport
    toggleActions: "play none none none", // play once
  }
});
```

### toggleActions Values

Format: `"onEnter onLeave onEnterBack onLeaveBack"`

| Use Case | Value |
|----------|-------|
| **Play once** (recommended) | `"play none none none"` |
| Play/reverse on scroll | `"play reverse play reverse"` |
| Play once, reset on leave | `"play none none reset"` |
| Restart every time | `"restart none none none"` |

## Pattern 2: Scrub (Scroll-Linked Progress)

```tsx
gsap.to(".parallax-bg", {
  y: -200,
  ease: "none",
  scrollTrigger: {
    trigger: ".parallax-section",
    start: "top bottom",
    end: "bottom top",
    scrub: 1,            // 1 second smoothing
  }
});
```

**Scrub values:**
- `true` — instant (scroll position = animation progress)
- `1` — 1s smoothing (recommended for parallax)
- `0.5` — 0.5s smoothing (snappier)
- `2` — 2s smoothing (very smooth, floaty)

## Pattern 3: Pin Section

```tsx
const tl = gsap.timeline({
  scrollTrigger: {
    trigger: ".pinned-section",
    start: "top top",
    end: "+=2000",         // pin for 2000px of scroll
    pin: true,
    scrub: 1,
  }
});

tl.from(".step-1", { opacity: 0, y: 50 })
  .to(".step-1", { opacity: 0 })
  .from(".step-2", { opacity: 0, y: 50 })
  .to(".step-2", { opacity: 0 })
  .from(".step-3", { opacity: 0, y: 50 });
```

## Pattern 4: Horizontal Scroll Section

```tsx
function HorizontalScroll() {
  const containerRef = useRef<HTMLDivElement>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);

  useGSAP(() => {
    const panels = gsap.utils.toArray<HTMLElement>(".panel");
    
    gsap.to(panels, {
      xPercent: -100 * (panels.length - 1),
      ease: "none",
      scrollTrigger: {
        trigger: wrapperRef.current,
        pin: true,
        scrub: 1,
        snap: 1 / (panels.length - 1),
        end: () => "+=" + wrapperRef.current!.offsetWidth,
      }
    });
  }, { scope: containerRef });

  return (
    <div ref={containerRef}>
      <div ref={wrapperRef} className="flex overflow-hidden">
        <div className="panel min-w-full">Section 1</div>
        <div className="panel min-w-full">Section 2</div>
        <div className="panel min-w-full">Section 3</div>
      </div>
    </div>
  );
}
```

## Pattern 5: Batch Stagger (Performance-Optimized)

```tsx
ScrollTrigger.batch(".card", {
  onEnter: (elements) => {
    gsap.from(elements, {
      opacity: 0,
      y: 40,
      stagger: 0.08,
      duration: 0.5,
      ease: "power2.out",
    });
  },
  start: "top 85%",
});
```

**Why batch?** Creates ONE ScrollTrigger for many elements instead of one per element. Much better performance for card grids.

## Pattern 6: Parallax Layers

```tsx
useGSAP(() => {
  // Background moves slow
  gsap.to(".bg-layer", {
    y: -100,
    scrollTrigger: {
      trigger: ".parallax-section",
      start: "top bottom",
      end: "bottom top",
      scrub: 1,
    }
  });

  // Midground moves medium
  gsap.to(".mid-layer", {
    y: -200,
    scrollTrigger: {
      trigger: ".parallax-section",
      start: "top bottom",
      end: "bottom top",
      scrub: 1,
    }
  });

  // Foreground moves fast
  gsap.to(".fg-layer", {
    y: -400,
    scrollTrigger: {
      trigger: ".parallax-section",
      start: "top bottom",
      end: "bottom top",
      scrub: 1,
    }
  });
}, { scope: sectionRef });
```

## Pattern 7: Progress-Linked Animations

```tsx
ScrollTrigger.create({
  trigger: ".article",
  start: "top top",
  end: "bottom bottom",
  onUpdate: (self) => {
    // self.progress = 0 to 1
    gsap.set(".progress-bar", { scaleX: self.progress });
  }
});
```

## Pattern 8: Class Toggle on Scroll

```tsx
ScrollTrigger.create({
  trigger: ".section",
  start: "top center",
  end: "bottom center",
  toggleClass: { targets: ".nav-link", className: "active" },
});
```

## Start/End Position Reference

```
start: "trigger-position viewport-position"
end:   "trigger-position viewport-position"
```

| Value | Meaning |
|-------|---------|
| `"top top"` | Element top meets viewport top |
| `"top 80%"` | Element top meets 80% down viewport (common reveal) |
| `"top center"` | Element top meets viewport center |
| `"center center"` | Element center meets viewport center |
| `"bottom bottom"` | Element bottom meets viewport bottom |
| `"top bottom"` | Element top meets viewport bottom (just entering) |
| `"+=2000"` | 2000px of scroll distance (for end with pin) |

## Responsive ScrollTrigger

```tsx
useGSAP(() => {
  const mm = gsap.matchMedia();

  mm.add({
    isDesktop: "(min-width: 1024px)",
    isTablet: "(min-width: 768px) and (max-width: 1023px)",
    isMobile: "(max-width: 767px)",
    reducedMotion: "(prefers-reduced-motion: reduce)",
  }, (context) => {
    const { isDesktop, isMobile, reducedMotion } = context.conditions!;

    if (reducedMotion) return; // no animations

    if (isDesktop) {
      // Full parallax + pinning
      gsap.to(".hero-bg", {
        y: -150,
        scrollTrigger: { trigger: ".hero", scrub: 1 }
      });
    }

    if (isMobile) {
      // Simple fade-in only
      gsap.from(".hero-content", {
        opacity: 0,
        duration: 0.6,
        scrollTrigger: { trigger: ".hero", start: "top 90%" }
      });
    }
  });
}, { scope: containerRef });
```

## Dynamic Content / Async Data

```tsx
useGSAP(() => {
  if (!data || data.length === 0) return;

  // Wait one frame for DOM to render
  requestAnimationFrame(() => {
    ScrollTrigger.refresh(); // recalculate positions

    ScrollTrigger.batch(".dynamic-card", {
      onEnter: (els) => gsap.from(els, { opacity: 0, y: 30, stagger: 0.08 }),
      start: "top 85%",
    });
  });
}, { scope: containerRef, dependencies: [data] });
```

## Debugging

```tsx
scrollTrigger: {
  markers: true,       // shows start/end markers (DEV ONLY)
  id: "hero-section",  // labels in markers
}
```

Remove `markers: true` before production.