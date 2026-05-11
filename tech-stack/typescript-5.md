# Tech-Stack: TypeScript 5

> [!NOTE]
> **TRIGGER:** LOAD ON frontend tasks, React development, Node.js scripts.
> **SCOPE:** TypeScript 5.x strict compilation standards, ES2024+ features.

## 1. Compiler Configuration
- Enforce `"strict": true` globally. No exceptions.
- Use `"moduleResolution": "Bundler"` for Next.js and modern bundler setups.
- Enable `"module": "NodeNext"` or `"Node16"` for Node.js backend scripts to correctly resolve ESM/CJS interop.
- Define and strictly use path aliases (`@/components/*`, `@/lib/*`) instead of relative paths.
- Enable `"isolatedDeclarations": true` for library code and shared packages to enforce explicitly typed exports that can be independently type-checked.

## 2. Type Safety & Patterns
- Rely on Discriminated Unions for complex state or API responses.
- Use Template Literal types for strictly typing dynamic strings (e.g., `type Event = \`user_${Action}\``).
- Apply `as const` (const assertions) for immutable literal types.
- Use the `satisfies` operator to validate object shapes without losing literal type information.
- Use the `using` keyword (Explicit Resource Management, ES2024) for deterministic disposal of resources (file handles, database connections, temp directories). Implement `Symbol.dispose` or `Symbol.asyncDispose` on resource classes.

## 3. Declaration Files
- Keep type declarations in `*.d.ts` files when creating global augmentations.
- Export interfaces and types from a dedicated `@/types` directory for shared domain logic.
- Use `--declaration` and `--declarationMap` for library packages to generate `.d.ts` files automatically.

## 4. Decorators & Metadata
- Use native TypeScript 5 decorators (TC39 Stage 3) — NOT the legacy `experimentalDecorators` flag.
- Leverage decorator metadata (`Symbol.metadata`) for dependency injection and ORM annotations when applicable.

## 5. Hard Constraints
- NEVER use the `any` type. Use `unknown` if the type is truly dynamic, then narrow it.
- NEVER use `@ts-ignore`. If necessary, use `@ts-expect-error` with a descriptive comment explaining why.
- ALWAYS explicitly type function return values for exported functions and Server Actions.
- NEVER use `experimentalDecorators` in new projects; use native TC39 decorators instead.

---

## ✅ TYPESCRIPT 5 COMPLIANCE CHECK (Mandatory)
- [ ] **Type Safety:** Is there zero usage of `any` or unjustified `@ts-expect-error`?
- [ ] **Advanced Types:** Are discriminated unions, `satisfies`, and `using` utilized effectively for strict typing?
- [ ] **Configuration:** Are strict compiler options, path aliases, and `isolatedDeclarations` (where applicable) adhered to?
- [ ] **Decorators:** Are native TC39 decorators used instead of the legacy experimental flag?
