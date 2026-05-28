# Phase 1: Planning & Architecture
> [!NOTE]
> Trigger: Starting new feature, refactoring, or planning session.

## Planning Protocol
- **Spec Teasing:** ⛔ generate large code blocks for new features without clarifying vagueness first. Stop & ask.
- **Chunking:** Present design plans in small, digestible chunks. Require explicit user sign-off.
- **Constraints:** Map environment, hardware, data scale, and deployment targets first.
- **Devil's Advocate:** Contrast the proposed architecture with a resource-efficient alternative.
- **Risk Matrix:** Evaluate Complexity, Data, Rollback, and Performance risks. Flag HIGH risks immediately.
- **Dependency Audit:** Check updates, security logs, and transitive dependencies before installing. Document justification.
- **Modeling:** Stress-test schemas. Plan relationships, FK constraints, indices, roles. Map indexing at 1x, 10x, 100x scale.
- **TDD & Agents:** Structure implementation to enforce Red/Green TDD. Use subagents for isolated task execution.
