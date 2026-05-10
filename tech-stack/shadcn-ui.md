# Tech-Stack: Shadcn/ui

> [!NOTE]
> **TRIGGER:** LOAD ON UI component creation, frontend styling, accessibility.
> **SCOPE:** Shadcn/ui, Radix UI primitives, Tailwind CSS v4.

## 1. Installation & Theming
- Use the Shadcn CLI to install components locally into `@/components/ui`.
- Customize themes heavily using CSS variables (`--primary`, `--radius`) in `globals.css`.
- Support seamless Dark Mode using `next-themes` and Tailwind's `dark:` variant.

## 2. Component Composition
- Treat Shadcn files as a starting point; extend and modify them as project requirements evolve.
- Maintain Accessibility (a11y) defaults provided by Radix UI primitives (e.g., keyboard navigation, ARIA attributes).
- Use the `cn()` utility (clsx + tailwind-merge) for clean, dynamic class name resolution.

## 3. UI Patterns
- Build compound components for complex UIs to avoid prop drilling.
- Extract common styling patterns into reusable classes or extend the Tailwind config.

## 4. Hard Constraints
- NEVER wrap Shadcn components in extra generic `div` tags just for spacing; use layout components.
- NEVER strip Radix UI accessibility features (like `Dialog.Title` or `aria-describedby`).
- ALWAYS run `npx shadcn-ui@latest add <component>` rather than copy-pasting from the docs to ensure versions match.

---

## ✅ SHADCN/UI COMPLIANCE CHECK (Mandatory)
- [ ] **Accessibility:** Are Radix primitives and ARIA roles preserved during modification?
- [ ] **Styling:** Is the `cn()` utility used correctly to prevent class clashes?
- [ ] **Theming:** Are CSS variables used for consistent theming and dark mode support?
