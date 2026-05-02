# PostCSS v8.x Standards

## 1. PIPELINE
- **Plugins:** Always include `autoprefixer`.
- **Nesting:** Use `postcss-nesting` or native CSS nesting where supported.

## 2. TAILWIND COMPATIBILITY
- **Integration:** Ensure `tailwindcss` is registered as a PostCSS plugin.
- **Processing:** Use `postcss-import` to manage large CSS architectures.
