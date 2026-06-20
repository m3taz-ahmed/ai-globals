[TECH] accessibility-standards
[OBJ] Global Accessibility (A11Y) Standards.
[RULES]
1. [REQ] WCAG 2.2 AA: Contrast 4.5:1 (normal) / 3:1 (large). NEVER remove `:focus` without custom alternative.
2. [REQ] Semantics: Use `<main>`, `<nav>`, `alt` on images, and `<label>` on forms.
3. [REQ] Dynamic: Use `aria-live`. Trap focus in modals. Use `role="status"`/`"alert"`.
4. [REQ] Audit: Must be 100% navigable by keyboard.
