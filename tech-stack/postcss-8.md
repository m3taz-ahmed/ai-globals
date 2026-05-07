# PostCSS v8.x Standards

> [!NOTE]
> **TRIGGER:** LOAD WHEN CONFIGURING POSTCSS OR ADDING CSS PROCESSING PLUGINS.
> **SCOPE:** POSTCSS PIPELINE, TAILWIND INTEGRATION, AND PLUGIN MANAGEMENT.

## 1. Pipeline Configuration
- **Core Plugin:** Always include `autoprefixer` with `browserslist` in `package.json`.
- **Nesting:** Use `postcss-nesting` or native CSS nesting where supported.
- **Imports:** Use `postcss-import` to manage large CSS architectures with `@import` statements.

## 2. Tailwind Compatibility
- **Integration:** Ensure `tailwindcss` is registered as a PostCSS plugin in `postcss.config.js`.
- **Processing:** Use `postcss-import` to manage large CSS architectures.
- **Order:** Plugins should be ordered: `postcss-import` → `tailwindcss` → `autoprefixer`. Tailwind must come before autoprefixer.

## 3. When PostCSS is Required vs Optional
- **Required:** When using custom PostCSS plugins (e.g., `postcss-pxtorem`, `postcss-css-variables`, `cssnano` for production minification).
- **Optional with Tailwind v4:** Tailwind v4 includes its own CSS processing engine (Oxide). PostCSS is not required unless you need additional plugins beyond Tailwind itself. See `tailwind-4-1.md` §5.

## 4. Production Optimization
- **Minification:** Use `cssnano` with `preset: ['default', { discardComments: { removeAll: true } }]` for production builds.
- **Purge:** Tailwind handles purge natively — do NOT add `@fullhuman/postcss-purgecss` when using Tailwind.

## 5. Configuration Pattern
```js
// postcss.config.js
export default {
    plugins: {
        'postcss-import': {},
        'tailwindcss': {},
        'autoprefixer': {},
        ...(process.env.APP_ENV === 'production' ? { 'cssnano': {} } : {}),
    },
};
```
