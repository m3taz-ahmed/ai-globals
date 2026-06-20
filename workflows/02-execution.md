[WORKFLOW] 02-execution
[OBJ] Code generation and development.
[RULES]
1. [REQ] Trigger: Writing/modifying code.
2. [PROHIBIT] Monolithic Dumps: Build ONE module at a time.
3. [REQ] Surgical Edits: Apply incremental diffs. Use `// ... existing code ...`. Do not rewrite entire files.
4. [REQ] TDD Workflow: Migration -> Model -> Service -> Controller -> Test.
5. [REQ] Token Efficiency: Do NOT output unchanged code.
6. [REQ] Checkpoints: Pause after milestones. Await approval.
