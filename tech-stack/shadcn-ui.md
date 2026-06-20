[TECH] shadcn-ui
[OBJ] Shadcn/ui & Radix Primitives.
[RULES]
1. [REQ] CLI: Use `npx shadcn@latest add` (NOT `shadcn-ui`). Use `shadcn blocks` for complex layouts.
2. [REQ] Theming: CSS variables (`globals.css`). `dark:` variant.
3. [REQ] Components: Extend locally in `@/components/ui`. Use `cn()` utility.
4. [PROHIBIT] Constraints: NEVER wrap in generic `div` for spacing. NEVER strip Radix ARIA accessibility.
5. [REQ] React Compiler: Do NOT manually add `useMemo`/`useCallback` to inner components.
