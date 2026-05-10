# Tech-Stack: TypeScript 5

> [!NOTE]
> **TRIGGER:** LOAD ON frontend tasks, React development, Node.js scripts.
> **SCOPE:** TypeScript 5.x strict compilation standards.

## 1. Compiler Configuration
- Enforce `"strict": true` globally. No exceptions.
- Use `"moduleResolution": "Bundler"` for Next.js and modern bundler setups.
- Define and strictly use path aliases (`@/components/*`, `@/lib/*`) instead of relative paths.

## 2. Type Safety & Patterns
- Rely on Discriminated Unions for complex state or API responses.
- Use Template Literal types for strictly typing dynamic strings (e.g., `type Event = \`user_${Action}\``).
- Apply `as const` (const assertions) for immutable literal types.
- Use the `satisfies` operator to validate object shapes without losing literal type information.

## 3. Declaration Files
- Keep type declarations in `*.d.ts` files when creating global augmentations.
- Export interfaces and types from a dedicated `@/types` directory for shared domain logic.

## 4. Hard Constraints
- NEVER use the `any` type. Use `unknown` if the type is truly dynamic, then narrow it.
- NEVER use `@ts-ignore`. If necessary, use `@ts-expect-error` with a descriptive comment explaining why.
- ALWAYS explicitly type function return values for exported functions and Server Actions.

---

## ✅ TYPESCRIPT 5 COMPLIANCE CHECK (Mandatory)
- [ ] **Type Safety:** Is there zero usage of `any` or unjustified `@ts-expect-error`?
- [ ] **Advanced Types:** Are discriminated unions and `satisfies` utilized effectively for strict typing?
- [ ] **Configuration:** Are strict compiler options and path aliases adhered to?
