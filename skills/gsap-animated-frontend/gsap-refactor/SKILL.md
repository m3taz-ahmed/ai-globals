---
name: gsap-refactor
description: Wrapper skill for Claude Code. Use when the user wants to improve or refactor motion on an existing page or component. Delegate to the shared gsap-animated-frontend package and follow its gsap-refactor workflow with persistent .gsap artifacts.
---

# GSAP Refactor Wrapper

This is a Claude-facing wrapper so `/gsap-refactor` appears as a direct command.

Use the shared package here:

- `~/.claude/skills/gsap-animated-frontend/SKILL.md`
- `~/.claude/skills/gsap-animated-frontend/subskills/gsap-refactor/SKILL.md`

## Required Flow

1. Read the root GSAP package skill.
2. Read the `gsap-refactor` subskill in the shared package.
3. Read current code and existing `.gsap` artifacts first.
4. Audit before changing motion direction.
5. Continue implementation through the shared package workflow.
