# Tech-Stack: Shadcn/ui

> [!NOTE]
> **TRIGGER:** LOAD ON UI component creation, frontend styling, accessibility.
> **SCOPE:** Shadcn/ui, Radix UI primitives, Tailwind CSS v4, Shadcn CLI v2.

## 1. Installation & Theming
- Use the Shadcn CLI (`npx shadcn@latest init`) to initialize the project with `components.json` configuration.
- Install components locally into `@/components/ui` using `npx shadcn@latest add <component>`.
- Customize themes heavily using CSS variables (`--primary`, `--radius`) in `globals.css`.
- Support seamless Dark Mode using `next-themes` and Tailwind's `dark:` variant.

## 2. Component Composition
- Treat Shadcn files as a starting point; extend and modify them as project requirements evolve.
- Maintain Accessibility (a11y) defaults provided by Radix UI primitives (e.g., keyboard navigation, ARIA attributes).
- Use the `cn()` utility (clsx + tailwind-merge) for clean, dynamic class name resolution.
- Use Shadcn's built-in component blocks and patterns (sidebar, charts, data-table) when available rather than building from scratch.

## 3. CLI & Registry
- Use `npx shadcn@latest add` (NOT `shadcn-ui@latest`) — the CLI was renamed to `shadcn`.
- Leverage the Shadcn Registry for community components (`npx shadcn@latest add https://registry.shadcn.com/r/...`) when extending beyond the default set.
- Use `npx shadcn@latest diff` after updating Shadcn to detect upstream component changes.

## 4. UI Patterns
- Build compound components for complex UIs to avoid prop drilling.
- Extract common styling patterns into reusable classes or extend the Tailwind config.
- Use the `Dialog`, `Sheet`, and `Popover` primitives consistently for overlays — never build custom modals that bypass Radix accessibility.

## 5. Hard Constraints
- NEVER wrap Shadcn components in extra generic `div` tags just for spacing; use layout components.
- NEVER strip Radix UI accessibility features (like `Dialog.Title` or `aria-describedby`).
- ALWAYS run `npx shadcn@latest add <component>` rather than copy-pasting from the docs to ensure versions match.
- NEVER use the deprecated `shadcn-ui` CLI command; use `shadcn` instead.

---

## ✅ SHADCN/UI COMPLIANCE CHECK (Mandatory)
- [ ] **Accessibility:** Are Radix primitives and ARIA roles preserved during modification?
- [ ] **Styling:** Is the `cn()` utility used correctly to prevent class clashes?
- [ ] **Theming:** Are CSS variables used for consistent theming and dark mode support?
- [ ] **CLI:** Is the correct `shadcn` CLI command used (not `shadcn-ui`)?
