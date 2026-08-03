---
name: responsive-tokens-example
---
[FILE] responsive-tokens-example
[OBJ] Compressed reference card for responsive design and design-token governance derived from Tailwind CSS, Bootstrap, shadcn/ui, daisyUI, Carbon, Semi Design.
[CONTEXT] Use when generating UI, building design systems, or enforcing consistency across breakpoints.
[RULES]
1. [TOKENS] Store primitives in one source of truth: colors, spacing, typography, radii, shadows, z-index, breakpoints.
2. [SEMANTIC] Expose semantic tokens (`primary`, `surface-elevated`, `text-muted`) over raw hex values.
3. [MOBILE-FIRST] Write base styles for mobile, then override at `sm`, `md`, `lg`, `xl` breakpoints.
4. [UTILITY] Use Tailwind utility classes as a constrained vocabulary; prohibit ad-hoc arbitrary values outside design tokens.
5. [COMPONENTS] Prefer unstyled/headless primitives (Radix) + a token layer (Tailwind/daisyUI/shadcn) for accessibility and theming.
6. [FRAMEWORK] Bootstrap/Foundation for rapid admin shells; Tailwind + shadcn/daisy for custom SaaS UIs; Carbon/Semi for enterprise dashboards.
7. [TEST] Validate responsive behavior on at least 3 real breakpoints and 1 reduced-motion preference.
8. [REFERENCES] `tailwindlabs/tailwindcss`, `twbs/bootstrap`, `shadcn-ui/ui`, `saadeghi/daisyui`, `carbon-design-system/carbon`, `DouyinFE/semi-design`.
