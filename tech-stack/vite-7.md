# Vite v7.x Standards

## 1. BUNDLING
- **Module Type:** Use `type: "module"` in `package.json`.
- **CSS:** Use PostCSS 8 and Tailwind CSS 4.

## 2. PERFORMANCE
- **Code Splitting:** Utilize dynamic imports for heavy components.
- **Minification:** Ensure `esbuild` is configured for production builds.

## 3. LARAVEL INTEGRATION
- **Plugin:** Use `laravel-vite-plugin` ^2.0.
- **Refresh:** Enable full page reload on Blade template changes.
