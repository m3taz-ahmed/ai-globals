[TECH] zod-validation
[OBJ] Zod v4 & Zod Mini.
[RULES]
1. [REQ] Version: Zod v4 (default). Zod Mini for client/edge bundles (size critical).
2. [REQ] API: `z.interface()` preferred over `z.object()` (faster, lazy eval). `.optional()` first class.
3. [REQ] Usage: `@hookform/resolvers/zod`. Type Server Actions. Parse API responses with `.safeParse()`.
4. [PROHIBIT] Constraints: NEVER trust API responses without validation. NEVER duplicate schemas (share them). NEVER use `zod/v3` imports.
