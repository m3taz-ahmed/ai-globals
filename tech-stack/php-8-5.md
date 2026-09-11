[TECH] php-8-5
[OBJ] PHP 8.5 Architecture Standards (Stable Nov 20 2025, latest 8.5.10 Aug 2026).
[RULES]
1. [REQ] Enums: Advanced pattern matching. Backed Enums with methods.
2. [REQ] JIT: No dynamic properties. Typed properties on hot paths.
3. [REQ] Typing: `declare(strict_types=1);` non-negotiable. Native Intersection/Union types. Pipe operator (`|>`) for functional transformations.
4. [REQ] Asymmetric Visibility (8.4+): `public private(set)` for read-only public props. Use in Filament resources to prevent UI mutation of model state.
5. [REQ] Property Hooks (8.4+): `public string $name { get => strtoupper($this->_name); set => $this->_name = strtolower($value); }`. Replace getters/setters with hooks.
6. [REQ] PCRE \C Forbidden: `\C` in UTF-8 patterns now forbidden (crash fix). Use `.` with `u` modifier instead.
7. [REQ] PDO_PGSQL Lazy Fetch: `PDO::ATTR_PREFETCH => 0` fixes (infinite loop in COPY, use-after-free, busy connection). Update to 8.5.10+ for these fixes.
8. [REQ] DOM Stack Overflow Fixes: Deep nesting no longer crashes `normalize()`, `isEqualNode()`, `setAttribute()`. Update to 8.5.10+ for DOM heavy apps (Filament rich editor).
