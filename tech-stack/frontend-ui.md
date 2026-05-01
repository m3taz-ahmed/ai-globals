# Frontend UI & JavaScript Standards

## 1. JAVASCRIPT ECOSYSTEM (ALPINE.JS FIRST)
- **Primary Tool:** For dynamic UI interactions within Blade/Filament, ALWAYS default to `Alpine.js` (`x-data`, `x-show`, `x-on`, etc.).
- **Vanilla JS:** If Vanilla JS is absolutely necessary for performance-heavy tasks (e.g., Canvas, WebGL, heavy DOM manipulation), write ES6+ modern JavaScript.
- **Strict Prohibition:** NEVER use jQuery or inject React/Vue inside a standard Blade view unless setting up a dedicated SPA/Inertia environment.

## 2. CSS & STYLING ARCHITECTURE
- **Tailwind Only:** Rely 100% on Tailwind CSS utility classes.
- **Custom CSS Restrictions:** Only write custom CSS (in `app.css`) when dealing with complex animations, third-party library overrides, or native CSS variables. 
- **No Specificity Wars:** Never use `!important` in custom CSS. Use Tailwind's arbitrary values (e.g., `w-[150px]`) instead of writing new CSS classes.

## 3. COMPONENTIZATION
- Extract repeatable UI elements into Anonymous Blade Components (`<x-button>`, `<x-card>`).
- Keep components "dumb" (they should only receive data via props and emit events).