[TECH] tailwind-3
[OBJ] Tailwind CSS v3.x Standards.
[RULES]
1. [REQ] Config: Rely on `tailwind.config.js`. Define exact content paths. Plugins (forms, typography, aspect-ratio).
2. [REQ] Layers: `@layer components`, `@layer utilities`. `@apply` sparingly.
3. [PROHIBIT] JIT: NEVER construct classes dynamically with string concat. Use Safelist if needed.
4. [REQ] Responsive: Mobile first -> `sm:`, `md:`, `lg:`. `dark:` variant.
