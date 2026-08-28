---
name: design-taste
description: Design DNA extractor — reverse-engineer any website's design taste into structured tokens and Taste DNA trade-offs via Playwright
---
[SKILL] design-taste
[OBJ] Reverse-engineer any website's design taste into a structured, reusable design system with evidence-backed trade-off reasoning.
[RULES]
1. [REQ] Triggers — Activate on: "/taste <url>", "analyze the design of X", "extract design tokens from X", "build something in the style of X".
2. [REQ] Prerequisite — Requires Playwright MCP. If unavailable, stop and instruct the user to enable it.
3. [REQ] Phase 1: Capture — Navigate to the target URL via Playwright MCP browser_navigate.
4. [REQ] Phase 1: Capture — Take a full-page screenshot via browser_screenshot for visual reference.
5. [REQ] Phase 1: Capture — Capture the accessibility snapshot via browser_snapshot to extract the DOM structure, computed styles, and layout.
6. [REQ] Phase 1: Capture — Scroll through the entire page capturing screenshots at each viewport to catch responsive and scroll-driven design changes.
7. [REQ] Phase 2: Measure — Extract color tokens: primary, secondary, accent, neutral, background, foreground, border, success/warning/error. Record hex + HSL.
8. [REQ] Phase 2: Measure — Extract typography tokens: font families (heading + body), font sizes (scale), font weights, line-heights, letter-spacing, text transforms.
9. [REQ] Phase 2: Measure — Extract spacing tokens: base unit, padding/margin scale, gap values, container max-width, section spacing.
10. [REQ] Phase 2: Measure — Extract radii tokens: border-radius scale (none, sm, md, lg, full).
11. [REQ] Phase 2: Measure — Extract shadow/elevation tokens: box-shadow scale, blur, spread, opacity.
12. [REQ] Phase 2: Measure — Extract grid/layout tokens: columns, gutters, breakpoints, container behavior (fixed/fluid), alignment patterns.
13. [REQ] Phase 2: Measure — Extract motion tokens: transition durations, easing functions, animation patterns, hover/focus state changes.
14. [REQ] Phase 3: Taste DNA — For each design decision, record a trade-off in the format: Trigger → Decision → Reason → Evidence.
15. [REQ] Phase 3: Taste DNA — Trigger: what design problem or constraint prompted the choice (e.g., "dense data display", "premium brand feel").
16. [REQ] Phase 3: Taste DNA — Decision: what the site chose to do (e.g., "used 4px base spacing unit", "employed high-contrast monochrome palette").
17. [REQ] Phase 3: Taste DNA — Reason: WHY this choice makes sense given the trigger and brand context.
18. [REQ] Phase 3: Taste DNA — Evidence: specific computed style values, screenshots, or DOM measurements that prove the decision.
19. [REQ] Phase 3: Taste DNA — Capture at least 10 trade-offs covering color, typography, spacing, layout, motion, and overall feel.
20. [REQ] Phase 3: Taste DNA — Reject generic descriptions like "clean and modern", "minimalist", "elegant" — demand specificity with measurable evidence.
21. [REQ] Phase 4: Output — Write a Markdown file named {domain}.md containing: overview, token tables, Taste DNA trade-offs, and usage guidance.
22. [REQ] Phase 4: Output — Write a JSON file named {domain}.json containing machine-readable tokens: colors, typography, spacing, radii, shadows, grid, motion.
23. [REQ] Phase 4: Output — Both files must be self-contained enough to reproduce the design system without revisiting the site.
24. [REQ] Phase 4: Output — Include a "reproduction checklist" in the Markdown: ordered steps to apply this taste to a new project.
25. [REQ] Quality — All color values must include both hex and HSL for dark-mode derivation.
26. [REQ] Quality — All spacing values must be expressed in the site's base unit (px or rem) and as a scale ratio.
27. [REQ] Quality — Note any responsive breakpoints and how tokens shift across them.
28. [REQ] Quality — Flag any accessibility concerns (contrast failures, small font sizes, missing focus states) observed during extraction.
29. [REQ] Quality — Record the extraction date and Playwright/browser version for reproducibility.
30. [PROHIBIT] Never output generic taste descriptions without evidence — "clean and modern" is a failure, not a result.
31. [PROHIBIT] Never skip the screenshot/DOM capture phase; visual inspection alone is insufficient.
32. [PROHIBIT] Never fabricate token values; every value must come from computed styles or DOM measurement.
33. [PROHIBIT] Never collapse the Taste DNA into a single paragraph; each trade-off must be a distinct, structured entry.
34. [CMD] Playwright MCP: browser_navigate — navigate to the target URL for capture.
35. [CMD] Playwright MCP: browser_snapshot — capture accessibility tree and DOM structure with computed styles.
36. [CMD] Playwright MCP: browser_screenshot — capture full-page and viewport screenshots for visual evidence.
37. [REQ] Phase 1: Capture — Record the viewport size, device pixel ratio, and user-agent for each capture session.
38. [REQ] Phase 1: Capture — Capture hover and focus states by interacting with interactive elements before screenshotting.
39. [REQ] Phase 1: Capture — Capture mobile and desktop viewports separately; do not assume tokens are identical across breakpoints.
40. [REQ] Phase 2: Measure — Extract border tokens: border widths, styles (solid, dashed), and colors per component type.
41. [REQ] Phase 2: Measure — Extract z-index scale and stacking context patterns (modals, dropdowns, tooltips, sticky headers).
42. [REQ] Phase 2: Measure — Extract opacity/overlay tokens for backdrops, disabled states, and scrim layers.
43. [REQ] Phase 2: Measure — Extract icon system: icon library, sizes, stroke width, and color inheritance pattern.
44. [REQ] Phase 3: Taste DNA — Identify the dominant design philosophy (e.g., Swiss grid, brutalist, neumorphic, flat, glassmorphic) with evidence.
45. [REQ] Phase 3: Taste DNA — Capture tension trade-offs: e.g., density vs whitespace, contrast vs harmony, personality vs professionalism.
46. [REQ] Phase 3: Taste DNA — Note where the site breaks its own rules (intentional inconsistency) and hypothesize why.
47. [REQ] Phase 4: Output — Include a "personality summary" — 3-5 adjectives backed by token evidence, not subjective opinion.
48. [REQ] Phase 4: Output — Include a "do/don't" section: patterns to replicate and patterns to avoid when applying this taste.
49. [REQ] Phase 4: Output — Include a Tailwind config snippet derived from the extracted tokens for immediate usability.
50. [REQ] Quality — Cross-reference token values across multiple pages/sections to confirm consistency vs intentional variation.
51. [REQ] Quality — If the site uses a CSS-in-JS or utility framework, note the framework and how it influences token structure.
52. [PROHIBIT] Never skip the Taste DNA phase — token tables alone do not capture design taste.
53. [PROHIBIT] Never output subjective adjectives without linking them to measured token evidence.
