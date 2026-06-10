---
name: subagent-driven-development
description: Execute an implementation plan by dispatching fresh subagents per task.
---
# Subagent-Driven Development

**Mode**: Plan execution via specialized subagents.

## 🔴 Core Principle
Fresh subagent per task + Two-stage review = High Quality.

## 🧱 The Process (Continuous)
1. Read the implementation plan.
2. For each task:
   - Dispatch `implementer` subagent with full task text.
   - If implementer asks questions, answer them.
   - Wait for implementer to finish (TDD + self-review).
   - Dispatch `spec-reviewer` subagent. If gaps exist, implementer fixes them.
   - Dispatch `code-quality-reviewer`. If issues exist, implementer fixes them.
3. Mark task complete.
4. Move to next task WITHOUT stopping to ask human partner (unless blocked).

**Red Flags**:
- NEVER start code quality review before spec compliance is approved.
- NEVER skip reviews or let implementer's self-review replace actual review.
- NEVER dispatch multiple implementers in parallel for dependent tasks.
