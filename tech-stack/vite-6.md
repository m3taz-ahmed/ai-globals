# Vite 6.x Build & Asset Standards

## 1. CONFIGURATION
- **Laravel Integration:** Use `laravel-vite-plugin` for seamless integration. Define entry points in `vite.config.js`:
  ```js
  import laravel from 'laravel-vite-plugin';
  export default defineConfig({
      plugins: [laravel({ input: ['resources/css/app.css', 'resources/js/app.js'] })],
  });
  ```
- **Environment API:** Use Vite's `import.meta.env` for environment variables. Prefix client-exposed vars with `VITE_`.

## 2. DEVELOPMENT
- **HMR:** Hot Module Replacement is enabled by default. Ensure `@vite` directive is in the Blade layout for HMR to work.
- **Dev Server:** `npm run dev` starts the Vite dev server. All assets are served through Vite's proxy during development.
- **HTTPS:** For HTTPS local development, configure Vite's `server.https` option or use `@vitejs/plugin-basic-ssl`.

## 3. PRODUCTION BUILD
- **Manifest:** `npm run build` generates a `manifest.json` in `public/build/`. Laravel reads this for asset versioning.
- **Code Splitting:** Use dynamic `import()` for route-based code splitting. Vite handles chunking automatically.
- **Tree Shaking:** Vite uses Rollup for production builds. Ensure all exports are statically analyzable for effective tree shaking.
- **Asset Hashing:** Production builds include content hashes in filenames for cache-busting. No manual versioning needed.

## 4. OPTIMIZATION
- **Dependency Pre-Bundling:** Vite pre-bundles `node_modules` dependencies with esbuild. Use `optimizeDeps.include` for packages that fail auto-detection.
- **CSS:** Tailwind CSS is processed by Vite's built-in PostCSS support (v3) or Tailwind's native engine (v4). No additional CSS tooling needed.
- **Images:** Use `?url` suffix for image imports. Consider `vite-imagetools` for responsive image generation.

## 5. RESTRICTIONS
- **No Webpack/Mix:** Laravel Mix is deprecated. Do not use Webpack or Mix in new projects. Migrate existing projects to Vite.
- **No CDN Fallbacks:** Do not load JS/CSS from external CDNs in development. Bundle everything through Vite for consistency and security.
