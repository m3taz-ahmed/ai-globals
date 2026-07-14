[FILE] anti-patterns
[OBJ] Strict negative constraints and forbidden practices.
[RULES]
1. [PROHIBIT] Logic in Controllers: Controllers call Services/Actions only.
2. [PROHIBIT] Duplication: Do not duplicate code in 3+ locations. Extract to utilities.
3. [PROHIBIT] Unmanaged TODOs: No `TODO`/`FIXME` without a ticket tag.
4. [PROHIBIT] DB Flaws: No tables without PKs. No FKs without `constrained()`. No `nullable()` without reason. Use `decimal(10,2)` for currency.
5. [PROHIBIT] Error Swallowing: No PHP `@` suppressions. No empty `catch{}`. No silent queue fails.
6. [PROHIBIT] Security Flaws: No CORS wildcard `*`. No internal traces in API. No plaintext passwords (use Argon2/bcrypt).
7. [PROHIBIT] Performance Killers: No `sleep()` in requests. No PHP memory limit `-1`. Stream large files instead of loading fully.
8. [PROHIBIT] AI Hallucinations: Verify ALL APIs/methods before calling. Never return hardcoded mock success.
9. [PROHIBIT] Version Guessing `[VER-01]`: ⛔ NEVER assume Filament=v3, Laravel=v11, or ANY default version. ALWAYS `composer.lock` → grep exact version → load correct `tech-stack/<pkg>-<ver>.md`. Defaulting to wrong version = shipping broken code.
