---
name: accessibility-auditor
description: Accessibility auditing for WCAG 2.2 AA compliance covering semantics, ARIA, keyboard, contrast, and screen readers
---
[SKILL] accessibility-auditor
[OBJ] Audit web interfaces for WCAG 2.2 AA conformance and ensure usable experiences for users of assistive technologies.
[RULES]
1. [REQ] Verify compliance with WCAG 2.2 Level AA success criteria across all audited pages and components.
2. [REQ] Use semantic HTML elements for their intended purpose (nav, main, button, table) before adding ARIA; ARIA supplements, not replaces, semantics.
3. [REQ] Apply correct ARIA roles, states, and properties only where semantics are insufficient; avoid redundant or conflicting ARIA.
4. [REQ] Ensure full keyboard navigation: every interactive element is reachable and operable via Tab, Shift+Tab, and activation keys.
5. [REQ] Verify color contrast ratios meet at least 4.5:1 for normal text and 3:1 for large text and UI component boundaries.
6. [REQ] Test with at least one screen reader (NVDA, VoiceOver, or JAWS) and confirm announced labels, roles, and states are accurate.
7. [REQ] Verify focus management: focus moves logically, is visible, and is trapped only intentionally within modals with an escape path.
8. [REQ] Support reduced motion: honor prefers-reduced-motion and provide non-animated alternatives for essential information.
9. [REQ] Provide RTL support: layouts, icons, and spacing mirror correctly under dir="rtl" and logical properties are used.
10. [CMD] Generate an audit report listing each failure, the WCAG criterion violated, the affected element, and the recommended fix.
11. [PROHIBIT] Conveying information by color alone; always pair color with text, icons, or patterns.
12. [PROHIBIT] Missing alt text on informative images and creating keyboard traps without an escape mechanism.
