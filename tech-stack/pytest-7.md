[TECH] pytest-7
[OBJ] pytest 7.x-8.x testing standards (constraint `>=7.0,<9.0`). See `pytest-8.md` for full rules.
[RULES]
1. [REQ] Same rules as `pytest-8.md`. This file covers the constraint range.
2. [REQ] `asyncio.run()` for async (NOT `get_event_loop()` — removed 3.14).
3. [REQ] `pytest.approx()` for floats. `pytest.importorskip()` for optional deps.
4. [REQ] Two-tier testing `[TEST-07]`: FAST (targeted) + FULL (before done).
[REFS]
- tech-stack/pytest-8.md (canonical detailed rules)
