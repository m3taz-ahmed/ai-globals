[WORKFLOW] 03-debugging
[OBJ] Advanced debugging and RCA.
[RULES]
1. [REQ] Format: Demand `[Error + Code + Logs]`.
2. [PROHIBIT] No Band-Aids: NO guessing. NO PHP `@` suppressions. NO disabling strict types. Apply permanent architectural fixes.
3. [REQ] Protocol: 1. Reproduce -> 2. Isolate (binary search) -> 3. Hypothesize -> 4. Verify -> 5. Regression Test.
4. [REQ] Post-Mortem: Document what/cause/fix/prevention/timeline in `state/MEMORY.md` for critical bugs.
