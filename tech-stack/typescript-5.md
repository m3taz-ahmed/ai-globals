[TECH] typescript-5
[OBJ] TypeScript 5.x Standards.
[RULES]
1. [REQ] Config: `"strict": true` globally. `"moduleResolution": "Bundler"`. `"isolatedDeclarations": true` for shared packages. Path aliases (`@/`).
2. [REQ] Types: Discriminated Unions. Template Literals. `satisfies` operator. `using` (Explicit Resource Management).
3. [PROHIBIT] Constraints: NEVER use `any`. NEVER use `@ts-ignore` (use `@ts-expect-error` with comment).
4. [REQ] Decorators: Native TC39 Stage 3 decorators (NO `experimentalDecorators`).
