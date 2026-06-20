[FILE] persistent-state-execution
[OBJ] State persistence architecture for complex tasks.
[RULES]
1. [REQ] Hidden State Directory `[EXE-PERSIST-01]`: Never rely on chat memory for multi-step tasks. Create a `.task/` or `.gsap/` directory.
2. [REQ] Directory Structure: Must contain `spec.md`, `plan.md`, `tasks/*.md`, and `phases/*/pXX-name.md`.
3. [REQ] One Phase At A Time: Execute exactly one phase file, verify it, then proceed.
4. [REQ] State Updates: Keep `tasks.md` and `plan.md` updated (`[x]`).
5. [REQ] GSAP Routing: Trigger `gsap-animated-frontend` skill for motion design to manage its `.gsap/` state.
