[SKILL] writing-plans
[OBJ] Create step-by-step implementation plan before coding.
[RULES]
1. [PROHIBIT] No Placeholders: Never write "TBD" or "TODO". Provide EXACT code blocks.
2. [REQ] Granular Tasks: 1. Fail Test -> 2. Minimal Code -> 3. Pass Test -> 4. Commit.
3. [REQ] File Paths: Always include exact file paths to create/modify.
4. [REQ] Format: Use exact structure:
   # [Feature] Implementation Plan
   **Goal:** ...
   **Architecture:** ...
   ### Task 1: [Component]
   **Files:** ...
   - [ ] Step 1: Write failing test (code block)
   - [ ] Step 2: Minimal implementation (code block)
