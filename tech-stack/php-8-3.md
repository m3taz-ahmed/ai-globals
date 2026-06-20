[TECH] php-8-3
[OBJ] PHP 8.3 Architecture Standards.
[RULES]
1. [REQ] Types: Typed Class Constants. Readonly reinitialization in `__clone()`. Anonymous readonly classes.
2. [REQ] JSON: `json_validate()` ONLY for pass-through. Use `json_decode(..., JSON_THROW_ON_ERROR)` if consuming.
3. [REQ] Bilingual UI: `mb_str_pad()` MANDATORY over `str_pad()`.
4. [REQ] Overrides: `#[\Override]` attribute is MANDATORY for overridden methods (enforce in CI).
5. [REQ] Randomizer: `Random\Randomizer` for all random values.
6. [PROHIBIT] Deprecations: NO dynamic properties (treat deprecation as error).
