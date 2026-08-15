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
10. [PROHIBIT] Folklore Engineering `[ARCH-01]` (Hazem Ali no-folklore rules): Do not name a pattern before naming the problem it solves. Do not introduce an interface without a client, substitution contract, or dependency boundary. Do not call a class single-responsibility because it is short — name the actors and reasons that cause it to change. Do not call a system Clean Architecture because its folders resemble concentric circles — inspect source dependency direction. Do not call a workload well-architected because it uses managed services — review requirements, critical flows, failure, security, cost, operations, performance.
11. [PROHIBIT] Source-Only Inference `[ARCH-02]`: Do not infer runtime behavior only from source code when optimization, concurrency, generated code, or native boundaries are relevant. Capture the effective execution contract.
12. [PROHIBIT] Multi-Variable Debugging `[ARCH-03]`: Do not change several variables in one debugging experiment unless the result remains discriminating.
13. [PROHIBIT] Passing-Test-As-Proof `[ARCH-04]`: Do not treat a passing test as proof when the test cannot observe the claimed failure class.
14. [PROHIBIT] Hidden Accepted Risk `[ARCH-05]`: Do not hide an accepted risk. Record its consequence, owner, expiry, and trigger for reconsideration.
15. [PROHIBIT] Governance Theater `[ARCH-06]`: Controls must exist in measurable runtime evidence, not only in documents. A policy check that runs only after user-visible output is governance theater.
16. [PROHIBIT] Ambient Authority `[ARCH-07]`: The model may propose, but only an independent control plane may authorize consequence. A policy decision cannot be reused across different targets. Output from tools is untrusted until revalidated at the next boundary.
