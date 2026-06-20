[SKILL] prompt-master-patterns
[OBJ] Fix 37 token-wasting AI prompting patterns.
[RULES]
1. [REQ] Task Patterns: Avoid vague verbs. Split multi-tasks. Define success criteria. Use explicit allow/deny lists. Remove emotional language. Use Phased Execution for large tasks.
2. [REQ] Context Patterns: Never assume prior knowledge (inject Memory Block). Always define stack, audience, and prior failures. Forbid hallucination.
3. [REQ] Format Patterns: Always define exact output format, length, persona, and aesthetic constraints. Add negative prompts for image gen.
4. [REQ] Scope Patterns: Define file boundaries and stack constraints. Set explicit stop conditions. Do not paste entire repos.
5. [REQ] Reasoning Patterns: Use Chain of Thought (CoT) for logic, but NEVER for o1/o3/Claude extended reasoning models. Inject memory per session to prevent contradiction.
6. [REQ] Agentic Patterns: Define starting/target states. Demand progress output. Lock filesystem (e.g. "Only edit src/"). Add human review gates. Fix Opus 4.7 contextrot via `/compact` or new sessions.
