---
name: gsap-new
description: Wrapper skill for Claude Code. Use when the user wants to animate a new page, new section, or greenfield GSAP experience. Delegate to the shared gsap-animated-frontend package and follow its gsap-new workflow with persistent .gsap artifacts.
---

# GSAP New Wrapper

This is a Claude-facing wrapper so `/gsap-new` appears as a direct command.

Use the shared package here:

- `~/.claude/skills/gsap-animated-frontend/SKILL.md`
- `~/.claude/skills/gsap-animated-frontend/subskills/gsap-new/SKILL.md`

## Required Flow

1. Read the root GSAP package skill.
2. Read the `gsap-new` subskill in the shared package.
3. Use `.gsap` artifacts as the source of truth.
4. Ask only missing questions.
5. Continue implementation through the shared package workflow.
