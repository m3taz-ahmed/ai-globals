---
name: test-guard
description: Guard test quality and coverage.
---
[SKILL] test-guard
[OBJ] Prevent AI test bloat and invalid mocking.
[RULES]
1. [REQ] Behavior: Test return values/state, not internal helper logic.
2. [REQ] Mocks: ONLY mock Network, DB, FS, LLM boundaries. NEVER mock internal classes or state.
3. [REQ] Efficiency: Merge duplicate setups into data-providers/parametrize. Delete trivial tests.
4. [REQ] DB: Queries MUST use a real test database.
5. [REQ] Names: `test_<scenario>_<expected_outcome>`.
6. [REQ] Pyramid enforcement: unit base (fast, isolated), integration middle (real boundaries), E2E thin (critical user paths only). Inverted pyramids (E2E-heavy) are slow, flaky, and cost more than they catch — flag the shape.
7. [REQ] Assertion quality: every test asserts an observable outcome — no assertion-free "smoke" tests, no asserting mocks were called as proof of correctness (verifies the mock, not the code), no catching-the-exception-then-passing.
8. [REQ] Determinism gate: no wall-clock reads (inject clock), no random without seed, no order-dependent tests, no shared mutable fixtures, no real network/disk in fast tier. A non-deterministic test is a flake in waiting.
9. [REQ] Fixture hygiene: factories/builders over fixture dumps; minimal data per test (create only what the assertion needs); teardown restores state — tests pollute nothing that outlives them.
10. [REQ] Coverage intent: cover branches + error paths + boundary values, not lines for the number. 100% line coverage with untested failure paths is a false certificate — review WHERE coverage is missing, not just how much.
11. [REQ] AI test bloat detection: flag tests that re-test the framework/language (testing that `map` maps), duplicated coverage through different layers, tautological assertions (`assert result == result`), or tests that exist only to inflate counts.
12. [REQ] Speed budget: fast tier <5s total; any test >1s needs justification (real DB hit, model load → mark + move to full tier); parallel-safe tests (no fixed ports, no shared tmp paths).
13. [REQ] Failure legibility: a failing test names the broken behavior without reading the code — good name + focused assert + actionable message. `test_failed` tells nobody anything.
14. [PROHIBIT] Tests that can't fail (always-true conditions), mocking the unit under test, `assert True` placeholders, catching broad exceptions to force green, or tests dependent on external services staying up.
