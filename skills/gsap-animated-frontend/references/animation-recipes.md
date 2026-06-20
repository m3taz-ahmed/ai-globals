# Animation Recipes — Copy-Paste Cookbook

Each recipe is a self-contained React component or pattern. Copy, adapt, ship.

---

## Hero Animations

### Recipe: Text Reveal Hero (Subtle & Professional)

```tsx
"use client";
import { useRef } from "react";
import { gsap } from "gsap";
import { useGSAP } from "@gsap/react";

export function HeroTextReveal() {
  const ref = useRef<HTMLDivElement>(null);

  useGSAP(() => {
    const tl = gsap.timeline({ defaults: { ease: "power3.out" } });

    tl.from(".hero-line", {
      y: 80,
      opacity: 0,
      duration: 0.9,
      stagger: 0.15,
    })
    .from(".hero-subtitle", {
      y: 20,
      opacity: 0,
      duration: 0.6,
    }, "-=0.4")
    .from(".hero-cta", {
      y: 15,
      opacity: 0,
      scale: 0.95,
      duration: 0.5,
      ease: "back.out(1.4)",
    }, "-=0.2")
    .from(".hero-badge", {
      x: -30,
      opacity: 0,
      duration: 0.5,
    }, "-=0.3");
  }, { scope: ref });

  return (
    <section ref={ref} className="relative min-h-screen flex items-center">
      <div className="max-w-4xl mx-auto px-6">
        <div className="overflow-hidden">
          <h1 className="hero-line text-5xl md:text-7xl font-bold opacity-0">
            Find the Perfect
          </h1>
        </div>
        <div className="overflow-hidden">
          <h1 className="hero-line text-5xl md:text-7xl font-bold opacity-0">
            School for Your Child
          </h1>
        </div>
        <p className="hero-subtitle text-xl mt-6 opacity-0">
          Discover top-rated schools across the UAE
        </p>
        <button className="hero-cta mt-8 px-8 py-4 rounded-xl text-lg font-semibold opacity-0">
          Start Exploring
        </button>
      </div>
    </section>
  );
}
```

### Recipe: Cinematic Zoom Hero

```tsx
useGSAP(() => {
  const tl = gsap.timeline();

  tl.from(".hero-bg-image", {
    scale: 1.3,
    duration: 2,
    ease: "power2.out",
  })
  .from(".hero-overlay", {
    opacity: 0,
    duration: 0.8,
  }, 0.3)
  .from(".hero-text", {
    y: 60,
    opacity: 0,
    duration: 1,
    ease: "power3.out",
  }, 0.6)
  .from(".hero-search-bar", {
    y: 30,
    opacity: 0,
    scale: 0.96,
    duration: 0.8,
    ease: "power2.out",
  }, 0.9);
}, { scope: ref });
```

### Recipe: Floating Shapes Background

```tsx
useGSAP(() => {
  const shapes = gsap.utils.toArray<HTMLElement>(".floating-shape");

  shapes.forEach((shape, i) => {
    gsap.to(shape, {
      y: `random(-30, 30)`,
      x: `random(-20, 20)`,
      rotation: `random(-15, 15)`,
      duration: `random(3, 6)`,
      ease: "sine.inOut",
      repeat: -1,
      yoyo: true,
      delay: i * 0.3,
    });
  });
}, { scope: ref });

// JSX: Scatter these absolutely positioned shapes behind content
// <div className="floating-shape absolute w-16 h-16 rounded-full bg-blue-500/10" />
```

---

## Card & Grid Animations

### Recipe: Staggered Card Reveal

```tsx
useGSAP(() => {
  ScrollTrigger.batch(".school-card", {
    onEnter: (elements) => {
      gsap.from(elements, {
        opacity: 0,
        y: 40,
        stagger: 0.08,
        duration: 0.6,
        ease: "power2.out",
      });
    },
    start: "top 85%",
  });
}, { scope: ref });
```

### Recipe: Card Hover Lift Effect

```tsx
useGSAP(() => {
  const cards = gsap.utils.toArray<HTMLElement>(".card-hover");

  cards.forEach((card) => {
    const image = card.querySelector(".card-image");

    card.addEventListener("mouseenter", () => {
      gsap.to(card, {
        y: -8,
        boxShadow: "0 20px 40px rgba(0,0,0,0.3)",
        duration: 0.3,
        ease: "power2.out",
      });
      if (image) {
        gsap.to(image, { scale: 1.05, duration: 0.4, ease: "power2.out" });
      }
    });

    card.addEventListener("mouseleave", () => {
      gsap.to(card, {
        y: 0,
        boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
        duration: 0.3,
        ease: "power2.out",
      });
      if (image) {
        gsap.to(image, { scale: 1, duration: 0.4, ease: "power2.out" });
      }
    });
  });
}, { scope: ref });
```

### Recipe: 3D Card Tilt on Mouse Move

```tsx
useGSAP(() => {
  const cards = gsap.utils.toArray<HTMLElement>(".tilt-card");

  cards.forEach((card) => {
    card.addEventListener("mousemove", (e) => {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;
      const rotateX = ((y - centerY) / centerY) * -8;  // max 8deg
      const rotateY = ((x - centerX) / centerX) * 8;

      gsap.to(card, {
        rotateX,
        rotateY,
        transformPerspective: 800,
        duration: 0.3,
        ease: "power2.out",
      });
    });

    card.addEventListener("mouseleave", () => {
      gsap.to(card, {
        rotateX: 0,
        rotateY: 0,
        duration: 0.5,
        ease: "power2.out",
      });
    });
  });
}, { scope: ref });
```

---

## Number & Stats Animations

### Recipe: Count Up Numbers

```tsx
useGSAP(() => {
  const counters = gsap.utils.toArray<HTMLElement>(".counter");

  counters.forEach((counter) => {
    const target = parseInt(counter.dataset.target || "0", 10);
    const obj = { value: 0 };

    gsap.to(obj, {
      value: target,
      duration: 2,
      ease: "power2.out",
      snap: { value: 1 },
      scrollTrigger: {
        trigger: counter,
        start: "top 80%",
        toggleActions: "play none none none",
      },
      onUpdate: () => {
        counter.textContent = obj.value.toLocaleString();
      },
    });
  });
}, { scope: ref });

// <span className="counter" data-target="15000">0</span>
```

### Recipe: Stats Card with Trend Arrow

```tsx
useGSAP(() => {
  const tl = gsap.timeline({
    scrollTrigger: {
      trigger: ".stats-section",
      start: "top 75%",
    }
  });

  tl.from(".stat-card", {
    opacity: 0,
    y: 30,
    stagger: 0.12,
    duration: 0.5,
    ease: "power2.out",
  })
  .from(".stat-number", {
    textContent: 0,
    snap: { textContent: 1 },
    duration: 1.5,
    stagger: 0.1,
    ease: "power2.out",
  }, "-=0.3")
  .from(".stat-arrow", {
    opacity: 0,
    y: 10,
    stagger: 0.08,
    duration: 0.3,
  }, "-=0.5");
}, { scope: ref });
```

---

## Text Animations

### Recipe: Word-by-Word Reveal (No SplitText Plugin)

```tsx
function SplitRevealText({ text, className }: { text: string; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);

  useGSAP(() => {
    const words = gsap.utils.toArray<HTMLElement>(".split-word");
    gsap.from(words, {
      opacity: 0,
      y: 20,
      duration: 0.5,
      stagger: 0.04,
      ease: "power2.out",
      scrollTrigger: {
        trigger: ref.current,
        start: "top 80%",
      }
    });
  }, { scope: ref });

  return (
    <div ref={ref} className={className}>
      {text.split(" ").map((word, i) => (
        <span key={i} className="split-word inline-block opacity-0 mr-[0.3em]">
          {word}
        </span>
      ))}
    </div>
  );
}
```

### Recipe: Typewriter Effect

```tsx
useGSAP(() => {
  const text = "Find your perfect school today";
  const el = document.querySelector(".typewriter")!;
  el.textContent = "";

  const tl = gsap.timeline({
    scrollTrigger: { trigger: el, start: "top 80%" }
  });

  text.split("").forEach((char, i) => {
    tl.to(el, {
      duration: 0.03,
      onComplete: () => { el.textContent += char; },
    }, i * 0.04);
  });

  // Blinking cursor
  tl.to(".cursor-blink", {
    opacity: 0,
    repeat: -1,
    yoyo: true,
    duration: 0.5,
    ease: "steps(1)",
  });
}, { scope: ref });
```

---

## Scroll Sections

### Recipe: Pinned Scene Transitions

```tsx
useGSAP(() => {
  const sections = gsap.utils.toArray<HTMLElement>(".scene");

  const tl = gsap.timeline({
    scrollTrigger: {
      trigger: ".scenes-container",
      start: "top top",
      end: `+=${sections.length * 100}%`,
      pin: true,
      scrub: 1,
    }
  });

  sections.forEach((section, i) => {
    if (i === 0) return;
    tl.from(section, { opacity: 0, y: 60, duration: 1 })
      .to(sections[i - 1], { opacity: 0, y: -60, duration: 1 }, "<");
  });
}, { scope: ref });
```

### Recipe: Background Color Transition on Scroll

```tsx
useGSAP(() => {
  const sections = gsap.utils.toArray<HTMLElement>(".color-section");
  const colors = ["#0a0f1a", "#1a1a2e", "#16213e", "#0f3460"];

  sections.forEach((section, i) => {
    gsap.to("body", {
      backgroundColor: colors[i],
      scrollTrigger: {
        trigger: section,
        start: "top center",
        end: "bottom center",
        scrub: 1,
      }
    });
  });
}, { scope: ref });
```

---

## Navigation Animations

### Recipe: Navbar Shrink on Scroll

```tsx
useGSAP(() => {
  ScrollTrigger.create({
    start: "top -80",
    onUpdate: (self) => {
      if (self.direction === 1) {
        // Scrolling down — shrink
        gsap.to(".navbar", {
          height: 60,
          backdropFilter: "blur(12px)",
          backgroundColor: "rgba(10, 15, 26, 0.9)",
          duration: 0.3,
        });
      } else {
        // Scrolling up — expand
        gsap.to(".navbar", {
          height: 80,
          backdropFilter: "blur(0px)",
          backgroundColor: "transparent",
          duration: 0.3,
        });
      }
    }
  });
}, { scope: ref });
```

### Recipe: Mobile Menu Reveal

```tsx
const menuTl = useRef<gsap.core.Timeline | null>(null);

useGSAP(() => {
  menuTl.current = gsap.timeline({ paused: true });

  menuTl.current
    .to(".menu-overlay", { opacity: 1, visibility: "visible", duration: 0.3 })
    .from(".menu-item", {
      x: 50,
      opacity: 0,
      stagger: 0.08,
      duration: 0.4,
      ease: "power2.out",
    }, "-=0.1");
}, { scope: ref });

// Toggle: menuTl.current?.play() or menuTl.current?.reverse()
```

---

## Special Effects

### Recipe: Magnetic Button

```tsx
function MagneticButton({ children }: { children: React.ReactNode }) {
  const ref = useRef<HTMLButtonElement>(null);

  useGSAP(() => {
    const btn = ref.current!;
    const xTo = gsap.quickTo(btn, "x", { duration: 0.4, ease: "power3" });
    const yTo = gsap.quickTo(btn, "y", { duration: 0.4, ease: "power3" });

    btn.addEventListener("mousemove", (e) => {
      const rect = btn.getBoundingClientRect();
      const x = e.clientX - rect.left - rect.width / 2;
      const y = e.clientY - rect.top - rect.height / 2;
      xTo(x * 0.3);  // 0.3 = magnetic strength
      yTo(y * 0.3);
    });

    btn.addEventListener("mouseleave", () => {
      xTo(0);
      yTo(0);
    });
  }, { scope: ref });

  return <button ref={ref}>{children}</button>;
}
```

### Recipe: Custom Cursor

```tsx
useGSAP(() => {
  const cursor = document.querySelector<HTMLElement>(".custom-cursor")!;
  const xTo = gsap.quickTo(cursor, "x", { duration: 0.5, ease: "power3" });
  const yTo = gsap.quickTo(cursor, "y", { duration: 0.5, ease: "power3" });

  document.addEventListener("mousemove", (e) => {
    xTo(e.clientX);
    yTo(e.clientY);
  });

  // Scale up on interactive elements
  const interactives = gsap.utils.toArray<HTMLElement>("a, button, .clickable");
  interactives.forEach((el) => {
    el.addEventListener("mouseenter", () => {
      gsap.to(cursor, { scale: 2, duration: 0.3 });
    });
    el.addEventListener("mouseleave", () => {
      gsap.to(cursor, { scale: 1, duration: 0.3 });
    });
  });
});

// JSX: <div className="custom-cursor fixed w-4 h-4 rounded-full bg-white/80 pointer-events-none z-[9999] mix-blend-difference" />
```

### Recipe: Reveal Mask (Clip-Path)

```tsx
useGSAP(() => {
  gsap.from(".masked-image", {
    clipPath: "inset(100% 0 0 0)",  // hidden from bottom
    duration: 1.2,
    ease: "power3.inOut",
    scrollTrigger: {
      trigger: ".masked-image",
      start: "top 75%",
    }
  });
}, { scope: ref });

// CSS: .masked-image { clip-path: inset(0 0 0 0); }
```

### Recipe: SVG Line Draw

```tsx
useGSAP(() => {
  const paths = gsap.utils.toArray<SVGPathElement>(".draw-path");

  paths.forEach((path) => {
    const length = path.getTotalLength();
    gsap.set(path, { strokeDasharray: length, strokeDashoffset: length });

    gsap.to(path, {
      strokeDashoffset: 0,
      duration: 2,
      ease: "power2.inOut",
      scrollTrigger: {
        trigger: path,
        start: "top 80%",
      }
    });
  });
}, { scope: ref });
```

---

## Page Transitions (Next.js App Router)

### Recipe: Fade + Slide Transition Wrapper

```tsx
"use client";
import { useRef } from "react";
import { useGSAP } from "@gsap/react";
import { gsap } from "gsap";

export function PageTransition({ children }: { children: React.ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);

  useGSAP(() => {
    gsap.from(ref.current, {
      opacity: 0,
      y: 20,
      duration: 0.5,
      ease: "power2.out",
    });
  }, { scope: ref });

  return <div ref={ref}>{children}</div>;
}

// Usage in layout: <PageTransition>{children}</PageTransition>
```

---

## Smooth Scrolling (Lenis Integration)

```tsx
"use client";
import { useEffect } from "react";
import Lenis from "lenis";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

export function SmoothScrollProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    const lenis = new Lenis({
      duration: 1.2,
      easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
    });

    lenis.on("scroll", ScrollTrigger.update);
    gsap.ticker.add((time) => lenis.raf(time * 1000));
    gsap.ticker.lagSmoothing(0);

    return () => {
      lenis.destroy();
      gsap.ticker.remove(lenis.raf);
    };
  }, []);

  return <>{children}</>;
}
```