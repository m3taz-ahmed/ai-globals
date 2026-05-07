# Vite v7.x Standards

> [!NOTE]
> **TRIGGER:** LOAD ON FRONTEND BUILD, ASSET BUNDLING, OR VITE CONFIGURATION TASKS.
> **SCOPE:** VITE 7 BUILD PIPELINE, LARAVEL INTEGRATION, AND PERFORMANCE OPTIMIZATION.

## 1. Bundling & Module System
- **Module Type:** Use `type: "module"` in `package.json`.
- **CSS:** Use Tailwind CSS 4 (includes its own CSS processing). PostCSS is optional — only include if custom PostCSS plugins are needed (see `tailwind-4-1.md` §5).
- **Entry Points:** Define multiple entry points in `vite.config.js` for multi-page applications using `rollupOptions.input`.

## 2. Performance Optimization
- **Code Splitting:** Utilize dynamic imports (`import()`) for heavy components and route-based splitting.
- **Minification:** Ensure `esbuild` is configured for production builds. Vite uses esbuild by default — do not replace with terser unless specific requirements demand it.
- **Tree Shaking:** Ensure all dependencies use ES modules for proper tree shaking. Verify with `rollup-plugin-visualizer` if bundle size is a concern.
- **Asset Inlining:** Configure `build.assetsInlineLimit` for small assets to reduce HTTP requests.

## 3. Laravel Integration
- **Plugin:** Use `laravel-vite-plugin` ^2.0.
- **Refresh:** Enable full page reload on Blade template changes via `refresh: true` in the plugin config.
- **Aliases:** Configure `@` alias pointing to `resources/js` for clean imports.
- **Hot Module Replacement:** Works out of the box with `npm run dev`. Ensure Vite dev server URL is accessible from the browser.

## 4. Development Experience
- **Dev Server:** Use `npm run dev` for development with HMR. Configure `server.host` for network access in team environments.
- **Environment Variables:** Use `VITE_` prefix for client-side env variables. Never expose server-side secrets.
- **Source Maps:** Enable source maps in development (`build.sourcery: true`). Disable in production unless monitoring tools require them.

## 5. Configuration Pattern
```js
// vite.config.js
import { defineConfig } from 'vite';
import laravel from 'laravel-vite-plugin';
import { resolve } from 'path';

export default defineConfig({
    plugins: [
        laravel({
            input: ['resources/css/app.css', 'resources/js/app.js'],
            refresh: true,
        }),
    ],
    resolve: {
        alias: { '@': resolve('./resources/js') },
    },
});
```
