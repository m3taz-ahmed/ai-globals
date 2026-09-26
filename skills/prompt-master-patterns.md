---
name: prompt-master-patterns
description: Prompt engineering patterns and best practices.
---
[SKILL] prompt-master-patterns
[OBJ] Fix 37 token-wasting AI prompting patterns.
[RULES]
1. [REQ] Task Patterns: Avoid vague verbs. Split multi-tasks. Define success criteria. Use explicit allow/deny lists. Remove emotional language. Use Phased Execution for large tasks.
2. [REQ] Context Patterns: Never assume prior knowledge (inject Memory Block). Always define stack, audience, and prior failures. Forbid hallucination.
3. [REQ] Format Patterns: Always define exact output format, length, persona, and aesthetic constraints. Add negative prompts for image gen.
4. [REQ] Scope Patterns: Define file boundaries and stack constraints. Set explicit stop conditions. Do not paste entire repos.
5. [REQ] Reasoning Patterns: Use Chain of Thought (CoT) for logic, but NEVER for o1/o3/Claude extended reasoning models. Inject memory per session to prevent contradiction.
6. [REQ] Agentic Patterns: Define starting/target states. Demand progress output. Lock filesystem (e.g. "Only edit src/"). Add human review gates. Fix Opus 4.7 contextrot via `/compact` or new sessions.
7. [REQ] Instruction placement: rules that must never break go in primacy position (top of system prompt); order-sensitive instructions group logically; the LAST instruction gets recency weight — put the output format last.
8. [REQ] Constraint vocabulary: prefer positive constraints ("respond in ≤3 bullet points") over negative-only ("don't be verbose"); negatives define what's banned, positives define what's wanted — both, in that order.
9. [REQ] Example-driven contracts: one concrete input→output example beats a paragraph of format description; edge-case examples (empty input, refusal case) pin behavior the spec can't fully enumerate.
10. [REQ] Iteration protocol: change ONE thing per prompt revision, keep the diff small, and re-eval — multi-variable prompt changes can't be attributed to causes; version each iteration (see `prompt-engineer`).
11. [REQ] Failure-mode prompting: tell the model what to do when it CAN'T comply ("if no answer found, say INSUFFICIENT_DATA — do not fabricate") — undefined failure paths default to hallucination.
12. [REQ] Anti-patterns catalog: roleplay-as-competence ("you are a 10x engineer" ≠ rigor), gratitude/threat theatrics ("this is important to my career"), kitchen-sink context dumps, asking for confidence scores the model can't produce, or chaining opinions ("what do you think about X" → generic hedging).
13. [PROHIBIT] CoT on reasoning-native models, assuming the model remembers across sessions, vague quality words without rubrics ("high quality", "detailed"), or shipping prompt changes without a regression check on known-good cases.
