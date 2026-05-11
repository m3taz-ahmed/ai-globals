# Tech-Stack: Zod Validation

> [!NOTE]
> **TRIGGER:** LOAD ON form validation, API response parsing, type guarding.
> **SCOPE:** Zod v4, Zod Mini, React Hook Form integration, TypeScript.

## 1. Zod v4 vs Zod Mini

- Use **Zod v4** (`zod`) as the default for full-featured validation (frontend forms, API routes, server-side).
- Use **Zod Mini** (`zod/v4/mini`) for edge/client bundles where bundle size is critical — it provides the same API with a fraction of the footprint.
- Both share the same `z` namespace and are interchangeable; migrate by changing the import path.
- Zod v4 introduces `z.interface()` (replacement for `z.object()` in many cases) with better performance and `.optional()` as a first-class modifier.

## 2. Schema Patterns
- Use schema composition (e.g., `.extend()`, `.omit()`, `.pick()`) to reuse validation logic.
- Use Discriminated Unions (`z.discriminatedUnion`) for complex payloads with different shapes.
- Implement `.transform()` to coerce types (e.g., string to Date) and `.refine()` for custom validation logic (e.g., password strength).
- Prefer `z.interface()` over `z.object()` for API contracts in Zod v4 — it is faster and supports lazy evaluation.
- Use `z.file()`, `z.blob()` for file upload validation in Server Actions.

## 3. Integration
- Integrate deeply with React Hook Form using `@hookform/resolvers/zod`.
- Share schemas between frontend and backend (where possible, e.g., Next.js API routes or monorepos) for single-source-of-truth validation.
- Parse API responses through Zod schemas (`schema.parse()`) to guarantee data shapes at runtime.
- Use Zod schemas to type Next.js Server Action inputs and outputs for end-to-end type safety.

## 4. Error Handling
- Customize error messages within the schema definition (e.g., `z.string({ required_error: "Name is required" })`).
- Utilize Zod v4's improved `flatten()` and `format()` methods to structure error responses for the frontend.
- Use the `errorMap` option for global error message customization across an entire schema tree.

## 5. Hard Constraints
- NEVER trust API responses without validation if the data shape is critical.
- NEVER duplicate validation logic between the UI and API if schemas can be shared.
- ALWAYS use `.safeParse()` instead of `.parse()` when handling untrusted data to avoid throwing unhandled exceptions.
- NEVER use `zod/v3` imports in a Zod v4 project; migrate all schemas to the v4 API.

---

## ✅ ZOD VALIDATION COMPLIANCE CHECK (Mandatory)
- [ ] **Integration:** Are React Hook Form forms leveraging the `zodResolver`?
- [ ] **Safety:** Are API responses or external payloads validated using `.safeParse()`?
- [ ] **Reusability:** Are base schemas composed and extended rather than duplicated?
- [ ] **Bundle Size:** Is Zod Mini used for client/edge bundles where size is critical?
