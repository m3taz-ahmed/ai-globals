---
name: web-design-guidelines
description: Vercel web interface guidelines — 100+ rules for accessibility, forms, dark mode, typography, animation, images, performance, navigation, touch, and i18n
---
[SKILL] web-design-guidelines
[OBJ] Apply production-grade web interface guidelines covering accessibility, forms, dark mode, typography, animation, images, performance, navigation, touch targets, and internationalization.
[RULES]
1. [REQ] Accessibility — Meet WCAG 2.2 Level AA across all pages and components.
2. [REQ] Accessibility — Use semantic HTML (nav, main, button, table) before ARIA; ARIA supplements, never replaces, semantics.
3. [REQ] Accessibility — Apply ARIA roles/states/properties only where semantics are insufficient; avoid redundant or conflicting ARIA.
4. [REQ] Accessibility — Ensure full keyboard navigation: every interactive element reachable via Tab, Shift+Tab, and activation keys.
5. [REQ] Accessibility — Verify color contrast ≥4.5:1 for normal text, ≥3:1 for large text and UI component boundaries.
6. [REQ] Accessibility — Manage focus: logical tab order, visible focus indicators, trap focus only intentionally in modals with escape path.
7. [REQ] Accessibility — Never convey information by color alone; pair color with text, icons, or patterns.
8. [REQ] Accessibility — Provide alt text on informative images; empty alt on decorative images.
9. [REQ] Accessibility — Test with at least one screen reader (NVDA, VoiceOver, JAWS).
10. [REQ] Accessibility — Provide skip-to-content link as the first focusable element.
11. [REQ] Accessibility — Maintain a visible focus ring on all interactive elements; never remove outline without replacement.
12. [REQ] Accessibility — Use aria-live="polite" for non-critical dynamic updates and aria-live="assertive" for critical alerts.
13. [REQ] Accessibility — Ensure touch targets have ≥44x44px hit area.
14. [REQ] Forms — Associate every input with a <label> via for/id; never rely on placeholder as label.
15. [REQ] Forms — Use autocomplete attributes for common fields (name, email, tel, address) to aid browser autofill.
16. [REQ] Forms — Use correct input types (email, tel, url, number, date) to trigger appropriate keyboards and validation.
17. [REQ] Forms — Validate on blur and submit, not on every keystroke; show inline errors near the field.
18. [REQ] Forms — Error messages must be specific, actionable, and associated via aria-describedby.
19. [REQ] Forms — Mark required fields with aria-required="true" and visible indicator (asterisk + sr-only text).
20. [REQ] Forms — Preserve user input across validation failures; never wipe the form on error.
21. [REQ] Forms — Disable submit button during request to prevent double-submission; re-enable on failure.
22. [REQ] Forms — Provide a success confirmation after submission, not just a silent redirect.
23. [REQ] Forms — Group related fields with <fieldset> and <legend>.
24. [REQ] Forms — Use inputmode="numeric" for numeric fields that should not trigger number spinners.
25. [REQ] Dark Mode — Use CSS custom properties for all colors; never hardcode hex values in components.
26. [REQ] Dark Mode — Support prefers-color-scheme media query for automatic switching.
27. [REQ] Dark Mode — Provide an explicit manual toggle that persists via localStorage or cookie.
28. [REQ] Dark Mode — Maintain contrast ratios in both themes; dark mode is not an excuse for low contrast.
29. [REQ] Dark Mode — Use system color-scheme meta tag: <meta name="color-scheme" content="light dark">.
30. [REQ] Dark Mode — Avoid pure black (#000) on pure white; prefer near-black (#0a0a0a) and near-white (#fafafa).
31. [REQ] Dark Mode — Dim images and videos in dark mode via filter brightness(0.85) when appropriate.
32. [REQ] Dark Mode — Ensure shadows are visible in dark mode; use lighter shadow colors or elevated surfaces.
33. [REQ] Typography — Set body line-height between 1.5 and 1.6 for readability.
34. [REQ] Typography — Minimum body font-size 16px; never go below 14px for readable content.
35. [REQ] Typography — Maintain consistent vertical rhythm using a base spacing unit (e.g., 4px or 8px grid).
36. [REQ] Typography — Use font-display: swap (or optional) to prevent FOIT and minimize FOUT.
37. [REQ] Typography — Preload critical font files: <link rel="preload" as="font" type="font/woff2" crossorigin>.
38. [REQ] Typography — Limit to 2 font families; one for headings, one for body, or a single variable font.
39. [REQ] Typography — Define a modular type scale (e.g., 1.250 major third) and stick to it.
40. [REQ] Typography — Use rem units for font-size; avoid px for text scaling with user preferences.
41. [REQ] Typography — Set max-width on text columns (65-75 characters) for optimal reading length.
42. [REQ] Typography — Use text-wrap: pretty or balance for headings to avoid orphaned words.
43. [REQ] Animation — Honor prefers-reduced-motion: reduce; disable or simplify non-essential animations.
44. [REQ] Animation — Keep UI transitions between 200-300ms; shorter feels abrupt, longer feels sluggish.
45. [REQ] Animation — Use ease-out for entering elements, ease-in for exiting, ease-in-out for state changes.
46. [REQ] Animation — Animate transform and opacity only; avoid animating layout properties (width, top, margin).
47. [REQ] Animation — Provide will-change sparingly and only on elements actively animating; remove after.
48. [REQ] Animation — Stagger list animations with 30-50ms increments, not uniform simultaneous entry.
49. [REQ] Animation — Never block the main thread with JavaScript-driven layout animations; use CSS or Web Animations API.
50. [REQ] Images — Always include width and height attributes to prevent CLS.
51. [REQ] Images — Use loading="lazy" on below-the-fold images; omit on above-the-fold critical images.
52. [REQ] Images — Provide srcset and sizes for responsive images to serve appropriate resolution.
53. [REQ] Images — Serve modern formats (AVIF, WebP) with <picture> fallback to JPG/PNG.
54. [REQ] Images — Use decoding="async" on non-critical images to reduce main-thread blocking.
55. [REQ] Images — Set fetchpriority="high" on the LCP image to prioritize loading.
56. [REQ] Images — Use appropriate aspect-ratio via CSS or attributes to reserve space before load.
57. [REQ] Images — Provide descriptive alt text for informative images; empty alt="" for decorative.
58. [REQ] Images — Inline critical SVG icons; avoid extra HTTP requests for small icons.
59. [REQ] Performance — Target LCP <2.5s on mobile 4G; identify and optimize the largest contentful element.
60. [REQ] Performance — Target INP <200ms; break long tasks into chunks and use requestIdleCallback.
61. [REQ] Performance — Target CLS <0.1; reserve space for ads, embeds, images, and dynamic content.
62. [REQ] Performance — Preload critical resources: fonts, LCP image, critical CSS.
63. [REQ] Performance — Defer non-critical JavaScript with defer or dynamic import.
64. [REQ] Performance — Minify and compress assets; enable Brotli or gzip.
65. [REQ] Performance — Use code-splitting at route boundaries; load feature code on demand.
66. [REQ] Performance — Inline critical CSS; load remaining CSS asynchronously.
67. [REQ] Performance — Use resource hints (preconnect, dns-prefetch) for third-party origins.
68. [REQ] Performance — Limit third-party scripts; audit with Lighthouse and Core Web Vitals.
69. [REQ] Performance — Serve static assets from a CDN with long cache headers and content hashing.
70. [REQ] Navigation — Provide a skip-to-main-content link as the first focusable element.
71. [REQ] Navigation — Use breadcrumbs for hierarchical sites; mark up withBreadcrumbList schema.
72. [REQ] Navigation — Indicate active/current state with aria-current="page" on nav links.
73. [REQ] Navigation — Use <nav> with aria-label for multiple navigation regions.
74. [REQ] Navigation — Ensure mobile navigation is keyboard accessible and focus-managed.
75. [REQ] Navigation — Provide a visible and accessible search mechanism for content-heavy sites.
76. [REQ] Navigation — Use descriptive link text; avoid "click here" or "read more" without context.
77. [REQ] Touch — Ensure all interactive elements have a minimum 44x44px touch target.
78. [REQ] Touch — Use touch-action CSS property to control gesture handling (pan-x, pan-y, manipulation).
79. [REQ] Touch — Add adequate spacing (≥8px) between adjacent touch targets to prevent mis-taps.
80. [REQ] Touch — Avoid hover-only interactions; ensure all functionality works on touch devices.
81. [REQ] Touch — Use pointer-events media queries to differentiate touch vs mouse interactions.
82. [REQ] Touch — Disable double-tap zoom delay with touch-action: manipulation on buttons and links.
83. [REQ] i18n — Set lang attribute on <html> and on elements in different languages.
84. [REQ] i18n — Support dir="rtl" for right-to-left languages; use CSS logical properties (margin-inline-start).
85. [REQ] i18n — Use ICU MessageFormat for pluralization and gender rules; never concatenate strings.
86. [REQ] i18n — Externalize all user-facing strings; never hardcode text in components.
87. [REQ] i18n — Use locale-aware date/number formatting (Intl.DateTimeFormat, Intl.NumberFormat).
88. [REQ] i18n — Avoid text in images; use styled HTML text for translatable content.
89. [REQ] i18n — Design layouts that accommodate text expansion (German ~30% longer than English).
90. [REQ] i18n — Use hreflang tags for multi-language pages to aid search engines.
91. [REQ] i18n — Test with pseudo-localization to catch hardcoded strings and layout overflow.
92. [REQ] i18n — Support both singular and plural forms; do not assume English pluralization rules.
93. [REQ] General — Use a consistent spacing scale (4px or 8px base) across the entire interface.
94. [REQ] General — Maintain a consistent border-radius scale; do not mix arbitrary radii.
95. [REQ] General — Use a defined shadow/elevation scale; avoid ad-hoc shadow values.
96. [REQ] General — Provide loading states (skeletons) for async content; never show blank screens.
97. [REQ] General — Provide empty states with guidance and next actions, not just "no data".
98. [REQ] General — Use 404 and 500 pages that are helpful and on-brand.
99. [REQ] General — Ensure all interactive elements have hover, focus, active, and disabled states.
100. [REQ] General — Test across browsers (Chrome, Firefox, Safari, Edge) and devices (mobile, tablet, desktop).
101. [REQ] General — Use semantic HTML landmarks (header, nav, main, aside, footer) for page structure.
102. [CMD] Context7 lookup: /vercel/next.js for Next.js image/font/script optimization patterns.
103. [CMD] Context7 lookup: /tailwindlabs/tailwindcss for dark mode, spacing, and responsive utilities.
104. [PROHIBIT] Never use color alone to convey meaning or state.
105. [PROHIBIT] Never remove focus outlines without an accessible replacement.
106. [PROHIBIT] Never hardcode color values in components; use design tokens / CSS custom properties.
107. [PROHIBIT] Never animate layout properties (width, height, top, left, margin, padding).
108. [PROHIBIT] Never use placeholder text as a label replacement.
109. [PROHIBIT] Never block the main thread with synchronous layout animations.
110. [PROHIBIT] Never ship images without width/height attributes or aspect-ratio reservation.
