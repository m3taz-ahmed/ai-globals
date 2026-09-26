---
name: test-driven-development
description: Test-driven development methodology.
---
[SKILL] test-driven-development
[OBJ] Red-Green-Refactor enforcement.
[RULES]
1. [PROHIBIT] Iron Law: NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST.
2. [REQ] Process: Write RED test -> Verify FAIL -> Write GREEN code (minimal/YAGNI) -> Verify PASS -> REFACTOR.
3. [REQ] The failing test is the spec: write it against the desired public interface before that interface exists — the red phase is where API design happens. Name tests as behavior sentences (`rejects_negative_quantity`), not method names.
4. [REQ] Minimal green: write the smallest code that passes — hardcoding an acceptable intermediate step (then triangulate with the next test). Resist solving the general case on the first cycle.
5. [REQ] Refactor on green only: restructure with the suite green, commit-refactor separately from behavior change. Test code gets the same refactoring discipline as production code.
6. [REQ] Test the contract, not the guts: assert on public behavior/outputs; tests coupled to private implementation make refactoring hostile — they should make it safe.
7. [REQ] Boundaries mocked, core real: fake at I/O edges (clock, network, DB, FS); domain logic runs real. One assert-concept per test; AAA structure; factories/builders over fixture soup.
8. [REQ] Speed discipline: unit suite stays <5s (sub-second ideal) — slow tests get marked and moved to the full tier; no real clock/network/filesystem in the fast tier.
9. [REQ] Bug workflow: every bug fix starts as a failing regression test reproducing the bug — the test proves the fix AND prevents the return.
10. [REQ] Coverage with teeth: chase branch coverage on critical logic; mutation-test mentally ("what code change escapes my tests?"); 100% coverage is not the goal — untested failure paths are the bug.
11. [PROHIBIT] Start Over If: Code written before test, test passed immediately, or cannot explain failure.
