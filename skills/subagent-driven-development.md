[SKILL] subagent-driven-development
[OBJ] Dispatch subagents for continuous task execution.
[RULES]
1. [REQ] Process: 
   - Read plan. 
   - Dispatch `implementer` per task. Wait for TDD self-review. 
   - Dispatch `spec-reviewer` to verify gaps.
   - Dispatch `code-quality-reviewer`. 
   - Mark task complete. Auto-move to next task.
2. [PROHIBIT] Red Flags: No parallel implementation of dependent tasks. NEVER skip quality/spec reviews.
