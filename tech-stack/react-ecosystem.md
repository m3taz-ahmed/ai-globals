# React & React Native Ecosystem (2025 Standards)

> [!IMPORTANT]
> This is the sovereign reference for all React-based development. Before starting any task, the agent MUST ask the user to choose between the frameworks/libraries listed below if not specified in `package.json`.

## 1. Web Frameworks
- **Next.js 15+ (App Router)**: Standard for SSR/SSG projects. Use `Server Components` by default.
- **Vite 6+**: Standard for SPA (Single Page Applications) or lightweight client-side tools.

## 2. Mobile (Native)
- **Expo SDK 52+**: The only managed workflow allowed.
- **Expo Router**: Use file-based routing for React Native.
- **NativeWind v4+**: For Tailwind CSS support in React Native.

## 3. State Management & Data Fetching
- **TanStack Query v5 (React Query)**: Mandatory for all server-side state (API fetching, caching, synchronization).
- **Zustand**: Mandatory for global client-side state (UI themes, auth session, modals). Avoid Redux unless explicitly requested.

## 4. UI & Styling (The "Wow Factor")
- **Tailwind CSS v4**: CSS-first configuration.
- **Shadcn UI**: Base component library. Customize with unique tokens.
- **Framer Motion**: Mandatory for micro-animations and transitions.
- **Lucide React / Lucide React Native**: Standard icon sets.

## 5. Forms & Validation
- **React Hook Form**: Standard for form logic.
- **Zod**: Mandatory for schema validation and TypeScript type inference.

## 6. Architectural Patterns
- **Atomic Design**: Structure components into `atoms`, `molecules`, `organisms`.
- **Compound Components**: Use for complex UI elements (Tabs, Modals, Selects).
- **Custom Hooks**: Extract all logic from components into dedicated hooks.
- **Bilingual Support (RTL/LTR)**: All components must support `dir="rtl"` and use logical CSS properties (e.g., `ms-2` instead of `ml-2`).

## 7. Quality Gates
- No `any` types in TypeScript.
- Every component must have a `types.ts` or inline interface.
- 100% test coverage for business logic using `Vitest` or `Jest`.
