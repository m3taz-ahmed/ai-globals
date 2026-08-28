---
name: accessibility-auditor
description: WCAG 2.2 AA Accessibility Auditor. 11 specialist agents covering every accessibility domain.
---
[SKILL] accessibility-auditor
[OBJ] Audit and remediate web interfaces for full WCAG 2.2 AA conformance across 11 domains.
[RULES]
1. [REQ] ARIA Semantics Agent: Verify correct ARIA roles, states, and properties.
   - Every interactive element must have an accessible name.
   - Use aria-label / aria-labelledby / aria-describedby appropriately.
   - Never duplicate native semantics with redundant ARIA (e.g., role="button" on <button>).
   - Test with screen readers: NVDA (Windows), VoiceOver (macOS), JAWS (Windows).

2. [REQ] Color Contrast Agent: Enforce WCAG contrast ratios across all text and UI.
   - Normal text (<18px): minimum 4.5:1 contrast ratio.
   - Large text (>=18px or >=14px bold): minimum 3:1.
   - UI components (borders, icons, focus indicators): minimum 3:1.
   - Disabled-state contrast must still be perceivable (not invisible).
   - Use relative luminance formula for calculation, not visual estimation.

3. [REQ] Keyboard Navigation Agent: Full keyboard operability with no traps.
   - Logical tab order matching visual reading order.
   - Focus must be visible (>=2px outline, 3:1 contrast against background).
   - No keyboard traps — user must be able to Tab out of any component.
   - Escape key closes modals, dialogs, and popovers.
   - Arrow-key navigation for composite widgets (tabs, menus, grids) per WAI-ARIA APG.

4. [REQ] Cognitive Accessibility Agent: Reduce cognitive load and prevent errors.
   - Use plain language (target grade-8 reading level).
   - Maintain consistent navigation patterns across pages.
   - Implement error prevention: confirm before destructive actions, allow undo.
   - Provide clear instructions before forms, not just error messages after.
   - Avoid time limits without warning and extension options.

5. [REQ] Forms Agent: Every input must be programmatically labeled and accessible.
   - Associate <label> with input via for/id, or wrap input inside <label>.
   - Group related fields with <fieldset> / <legend>.
   - Inline validation with accessible error messages (aria-describedby, role="alert").
   - Set autocomplete attributes for personal-info fields (name, email, tel, address).
   - Required fields indicated via aria-required and a visual cue (asterisk + text).

6. [REQ] Images Agent: Correct text alternatives for every image type.
   - Informative images: concise, descriptive alt text.
   - Decorative images: alt="" or aria-hidden="true".
   - Complex images (charts, diagrams): longdesc or visible caption with aria-describedby.
   - Functional images (buttons, links): alt describes the action, not the image.
   - No missing alt attributes — every <img> must have an alt attribute (even if empty).

7. [REQ] Media Agent: Synchronized alternatives for all audio and video.
   - Prerecorded video: synchronized captions (WCAG 1.2.2).
   - Prerecorded audio: full transcript (WCAG 1.2.1).
   - Video with important visual info: audio description (WCAG 1.2.5).
   - Live audio: live captions (WCAG 1.2.4).
   - Media player must be keyboard accessible (play, pause, seek, volume).

8. [REQ] Structure Agent: Semantic landmarks and logical heading hierarchy.
   - Use HTML5 landmarks: <header>, <nav>, <main>, <aside>, <footer>.
   - Exactly one <main> element per page.
   - Heading hierarchy must be logical: h1 > h2 > h3, no skipped levels.
   - Use <section> with aria-label when a heading is not visually displayed.
   - Every page must have a descriptive <title> that changes per route.

9. [REQ] Motion and Animation Agent: Respect user motion preferences.
   - Honor prefers-reduced-motion: reduce — disable or simplify non-essential animations.
   - No content flashing more than 3 times per second (photosensitive seizure threshold).
   - Auto-playing motion longer than 5s must have pause, stop, or hide control.
   - Parallax and auto-scroll must be user-controllable and pausable.

10. [REQ] Touch and Mobile Agent: Adequate targets and reflow on small screens.
    - Touch targets minimum 44x44 CSS pixels with adequate spacing between targets.
    - Provide alternatives to complex gestures (pinch, multi-swipe) — at least one single-pointer alternative.
    - No content loss on zoom to 200% (reflow at 320 CSS px width).
    - No horizontal scroll at 1280px viewport width.

11. [REQ] Internationalization Agent: Language and BiDi support.
    - Set lang attribute on <html> and override per-element for language changes.
    - Support dir="rtl" for RTL languages (Arabic, Hebrew, Persian).
    - Use logical CSS properties (margin-inline-start) over physical (margin-left).
    - Mirror layouts, icons, and directional cues correctly in BiDi contexts.
    - Ensure form labels, error messages, and date formats are translatable.

[CMD] Audit tools:
- axe-core: `npx @axe-core/cli <url> --tags wcag2aa,wcag22aa --save axe-report.json`
- WAVE: `npx wave-runner <url>` or browser extension
- Lighthouse: `npx lighthouse <url> --only-categories=accessibility --output=html --output-path=./a11y-report.html`
- Pa11y: `npx pa11y <url> --standard=WCAG2AA`
- Screen reader testing: NVDA (Windows), VoiceOver (macOS), TalkBack (Android)
[CMD] Context7: `/dequelabs/axe-core` for axe-core API, custom rules, and rule documentation.
