---
name: image-to-code
description: Image-first website design-to-code workflow — generate design images first, analyze deeply, then implement pixel-faithful frontend
---
[SKILL] image-to-code
[OBJ] Convert design intent into production frontend by generating design images first, analyzing them deeply, then implementing to match — never skip the image generation phase.
[RULES]
1. [REQ] Phase 1: Generate — Design images are MANDATORY. Never skip image generation and jump to code.
2. [REQ] Phase 1: Generate — Generate ENOUGH images: one per major section (hero, features, pricing, footer) rather than one compressed board.
3. [REQ] Phase 1: Generate — One image per section is the baseline; a single compressed mood board is insufficient for faithful implementation.
4. [REQ] Phase 1: Generate — Specify the section name, purpose, and content in each image generation prompt for targeted output.
5. [REQ] Phase 1: Generate — Keep the hero section clean, spacious, and readable — avoid cluttering above the fold.
6. [REQ] Phase 1: Generate — Define design parameters in every prompt: DESIGN_VARIANCE=8, MOTION_INTENSITY=5, VISUAL_DENSITY=6.
7. [REQ] Phase 1: Generate — DESIGN_VARIANCE=8: introduce meaningful variety in layout, color, and component patterns across sections.
8. [REQ] Phase 1: Generate — MOTION_INTENSITY=5: moderate animation — present but not overwhelming; enhances rather than distracts.
9. [REQ] Phase 1: Generate — VISUAL_DENSITY=6: balanced density — enough content to feel substantial, enough whitespace to breathe.
10. [REQ] Phase 2: Analyze — Perform deep image analysis on every generated image before writing code.
11. [REQ] Phase 2: Analyze — Extract the color system: background, foreground, primary, secondary, accent, border, and state colors with hex values.
12. [REQ] Phase 2: Analyze — Extract the typography system: font families, size scale, weights, line-heights, and letter-spacing per element.
13. [REQ] Phase 2: Analyze — Extract the spacing system: section padding, component gaps, and the base spacing unit.
14. [REQ] Phase 2: Analyze — Extract the layout grid: columns, gutters, breakpoints, container width, and alignment per section.
15. [REQ] Phase 2: Analyze — Extract component patterns: card styles, button variants, input styles, navigation structure, and footer layout.
16. [REQ] Phase 2: Analyze — Document the extracted system as a token table before implementation begins.
17. [REQ] Phase 3: Implement — Build frontend that matches the analyzed design system pixel-faithfully.
18. [REQ] Phase 3: Implement — Use the extracted tokens as CSS custom properties or Tailwind config — never hardcode values.
19. [REQ] Phase 3: Implement — Implement responsive behavior inferred from the design images; do not guess breakpoints arbitrarily.
20. [REQ] Phase 3: Implement — Keep the hero spacious and readable — large headline, clear subtext, single primary CTA, generous whitespace.
21. [REQ] Phase 3: Implement — Avoid cards-inside-cards-inside-cards — limit nesting depth to two levels maximum.
22. [REQ] Phase 3: Implement — Each section must have clear visual separation via spacing, background, or divider — not just borders.
23. [REQ] Phase 3: Implement — Match the motion intensity (MOTION_INTENSITY=5): subtle hover states, smooth scroll, fade-in on viewport entry.
24. [REQ] Phase 3: Implement — Honor prefers-reduced-motion for all animations.
25. [REQ] Phase 3: Implement — Ensure accessibility: semantic HTML, alt text, keyboard nav, contrast ratios per WCAG 2.2 AA.
26. [REQ] Phase 3: Implement — Use modern image formats (AVIF/WebP) and lazy-load below-the-fold images.
27. [REQ] Phase 3: Implement — Set width/height on all images to prevent CLS.
28. [REQ] Quality — Compare the implemented result against the generated images section-by-section before declaring done.
29. [REQ] Quality — If the implementation diverges from the image, fix the implementation — the image is the source of truth.
30. [REQ] Quality — Run Lighthouse and Core Web Vitals checks; target LCP <2.5s, INP <200ms, CLS <0.1.
31. [PROHIBIT] Never skip the image generation phase — coding without a visual reference produces generic results.
32. [PROHIBIT] Never use a single compressed mood board as the sole reference — generate per-section images.
33. [PROHIBIT] Never nest cards more than two levels deep — avoid cards-inside-cards-inside-cards.
34. [PROHIBIT] Never clutter the hero — one headline, one subtext, one CTA, generous whitespace.
35. [PROHIBIT] Never hardcode design values — extract tokens from the image analysis and use them consistently.
36. [CMD] Image generation: use the available image generation tool/MCP to produce per-section design images with DESIGN_VARIANCE=8, MOTION_INTENSITY=5, VISUAL_DENSITY=6.
37. [CMD] Image analysis: use vision/image-understanding capabilities to extract design tokens from each generated image.
38. [REQ] Phase 1: Generate — Generate a hero image first; it sets the tone, color direction, and personality for all subsequent sections.
39. [REQ] Phase 1: Generate — Maintain visual consistency across section images: same color palette, typography, and spacing language.
40. [REQ] Phase 1: Generate — Vary layout patterns across sections (alternating image/text, grid, full-bleed) to achieve DESIGN_VARIANCE=8.
41. [REQ] Phase 1: Generate — Include realistic content (headlines, body text, CTAs) in images — not lorem ipsum or blank placeholders.
42. [REQ] Phase 1: Generate — Specify the target device/viewport in the prompt (desktop, mobile, or both) to get proportionally correct output.
43. [REQ] Phase 2: Analyze — Extract the visual hierarchy: identify primary, secondary, and tertiary elements by size, weight, and position.
44. [REQ] Phase 2: Analyze — Extract the mood/personality: is it playful, serious, premium, technical? Record with visual evidence.
45. [REQ] Phase 2: Analyze — Identify reusable component patterns (cards, buttons, badges, tabs) and document their anatomy.
46. [REQ] Phase 2: Analyze — Note the whitespace strategy: generous, tight, or asymmetric — and the base spacing unit.
47. [REQ] Phase 3: Implement — Build section-by-section in the order they appear; do not jump to footer before hero is done.
48. [REQ] Phase 3: Implement — Use a consistent component library (shadcn/ui, Radix, or custom) — do not mix UI systems.
49. [REQ] Phase 3: Implement — Ensure the navigation matches the design image — logo position, menu style, CTA placement.
50. [REQ] Phase 3: Implement — Match button styles exactly: padding, border-radius, font-weight, shadow, hover/active states.
51. [REQ] Phase 3: Implement — Reproduce the exact border-radius language — do not mix sharp corners with rounded corners arbitrarily.
52. [REQ] Quality — Take a screenshot of the implemented page and overlay it against the design image for a visual diff.
53. [REQ] Quality — Verify text content matches the image — do not paraphrase headlines or change CTA labels without approval.
54. [PROHIBIT] Never implement a section without a corresponding design image for that section.
55. [PROHIBIT] Never mix design languages from different images — maintain one consistent system throughout.
