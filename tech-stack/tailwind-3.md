# Tailwind CSS v3.x Standards

## 1. CONFIGURATION
- **Config File:** Heavily reliant on `tailwind.config.js` for extending themes, colors, fonts, and spacing.
- **Content Paths:** Define precise content paths to avoid scanning unnecessary files. Use glob patterns effectively.
- **Plugins:** Use `@tailwindcss/forms`, `@tailwindcss/typography`, and `@tailwindcss/aspect-ratio` for common patterns.

## 2. DIRECTIVES & LAYERS
- **Required:** Standard `@tailwind base; @tailwind components; @tailwind utilities;` directives.
- **Custom Layers:** Use `@layer components {}` for reusable component styles. Use `@layer utilities {}` for custom utilities.
- **@apply:** Use sparingly — only in component CSS files. Prefer utility classes directly in HTML.

## 3. JIT MODE
- **Always On:** JIT (Just-In-Time) mode is default in v3. Arbitrary values (e.g., `w-[137px]`, `bg-[#1a1a2e]`) are fully supported.
- **Dynamic Classes:** Never construct class names dynamically with string concatenation. Use complete class names for JIT to detect them.

## 4. PURGING & PRODUCTION
- **Tree Shaking:** JIT mode only generates used classes. Ensure all class names are statically analyzable.
- **Safelist:** Use `safelist` in config for dynamically generated classes that can't be statically detected.
- **Minification:** Production builds auto-minify CSS. No additional tooling needed.

## 5. RESPONSIVE & DARK MODE
- **Mobile First:** Write base styles for mobile, then use `sm:`, `md:`, `lg:`, `xl:`, `2xl:` for larger breakpoints.
- **Dark Mode:** Use `dark:` variant. Configure `darkMode: 'class'` for manual toggle support.