[WORKFLOW] 12-audit-ui
[OBJ] Elite UI/UX, aesthetics, and visual performance teardown.
[TRIGGER] `/audit-ui`
[PERSONA] Principal Architect + World-Class UI/UX Engineer
[RULES]
1. [REQ] Scope: Filament panels, Blade, Livewire, Inertia/Vue/React, CSS/Tailwind, public web.
2. [REQ] Pre-flight: Read `tech-stack/design-foundations.md`, `rules/anti-patterns.md`.
3. [REQ] Scan Targets:
   - Typography, color systems (OKLCH), spacing, RTL/LTR parity
   - Glassmorphism, micro-interactions, Bento layouts where appropriate
   - Filament: themes, SPA, lazy relation managers, widget performance
   - Accessibility (contrast, focus, ARIA), mobile responsiveness
   - Generic/boilerplate UI patterns (⛔ rejected per global-roles)
4. [REQ] Output Language: **Arabic** (technical terms/code in English).
5. [REQ] Per finding format:
   - **المشكلة** | **الحل الإيليت** | **التأثير** | **المميزات والعيوب**
6. [REQ] End with prioritized action table + offer `/execute [Target]`.
7. [PROHIBIT] Auto-fix without explicit `/execute` approval.
