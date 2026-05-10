# Tech-Stack: Zod Validation

> [!NOTE]
> **TRIGGER:** LOAD ON form validation, API response parsing, type guarding.
> **SCOPE:** Zod, React Hook Form integration, Typescript.

## 1. Schema Patterns
- Use schema composition (e.g., `.extend()`, `.omit()`, `.pick()`) to reuse validation logic.
- Use Discriminated Unions (`z.discriminatedUnion`) for complex payloads with different shapes.
- Implement `.transform()` to coerce types (e.g., string to Date) and `.refine()` for custom validation logic (e.g., password strength).

## 2. Integration
- Integrate deeply with React Hook Form using `@hookform/resolvers/zod`.
- Share schemas between frontend and backend (where possible, e.g., Next.js API routes or monorepos) for single-source-of-truth validation.
- Parse API responses through Zod schemas (`schema.parse()`) to guarantee data shapes at runtime.

## 3. Error Handling
- Customize error messages within the schema definition (e.g., `z.string({ required_error: "Name is required" })`).
- Utilize Zod's `format()` or `flatten()` to structure error responses for the frontend.

## 4. Hard Constraints
- NEVER trust API responses without validation if the data shape is critical.
- NEVER duplicate validation logic between the UI and API if schemas can be shared.
- ALWAYS use `.safeParse()` instead of `.parse()` when handling untrusted data to avoid throwing unhandled exceptions.

---

## ✅ ZOD VALIDATION COMPLIANCE CHECK (Mandatory)
- [ ] **Integration:** Are React Hook Form forms leveraging the `zodResolver`?
- [ ] **Safety:** Are API responses or external payloads validated using `.safeParse()`?
- [ ] **Reusability:** Are base schemas composed and extended rather than duplicated?
