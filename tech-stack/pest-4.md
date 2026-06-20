[TECH] pest-4
[OBJ] Pest v4.x Testing Standards.
[RULES]
1. [REQ] Arch Testing: `arch()` expectations to enforce boundaries.
2. [REQ] Organization: 1 test file per Controller/Service. Use `with()` for parameterized datasets.
3. [REQ] Syntax: `expect()` exclusively. ⛔ NO PHPUnit assertions.
4. [REQ] Performance: `--parallel` for CI. Prefer `DatabaseTransactions` over `RefreshDatabase` when possible.
