# Global Accessibility (A11Y) Standards

## 1. WCAG 2.1 AA COMPLIANCE GATE
- **Contrast Ratio:** Minimum `4.5:1` for normal text and `3:1` for large text/UI components.
- **Focus Indicators:** Never remove `:focus` outlines without providing a high-visibility custom alternative.
- **Screen Readers:** Use semantic HTML (`<main>`, `<nav>`, `<header>`, `<article>`). Every image MUST have an `alt` attribute.
- **Form Labels:** Every input must have a corresponding `<label>` or `aria-label`.

## 2. DYNAMIC CONTENT
- **Live Regions:** Use `aria-live` for notifications and dynamic updates.
- **Modals:** Implement focus trapping. Focus must move to the modal when opened and return to the trigger when closed.
- **Status Messages:** Use `role="status"` or `role="alert"` for feedback.

## 3. AUDIT TOOLS
- Use `axe-core` or Lighthouse for automated audits.
- Manual check: Can the entire application be used with ONLY a keyboard?
