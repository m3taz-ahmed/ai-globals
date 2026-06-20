[TECH] postcss-8
[OBJ] PostCSS v8.x Standards.
[RULES]
1. [REQ] Pipeline: `autoprefixer` + `browserslist`. `postcss-nesting`. `postcss-import`.
2. [REQ] Tailwind: `postcss-import` -> `tailwindcss` -> `autoprefixer`.
3. [REQ] Usage: Optional with Tailwind v4 UNLESS custom plugins needed (`postcss-pxtorem`, etc.).
4. [REQ] Prod: `cssnano` (discardComments). ⛔ NO `@fullhuman/postcss-purgecss` (Tailwind handles it).
