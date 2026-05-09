# Contributing to AI Global OS

> [!IMPORTANT]
> By contributing, you are helping to raise the **global standard for AI-driven engineering**. Every rule file, tech-stack standard, and workflow you add will be enforced across all projects that use this system. Contributions carry real architectural weight.

---

## Table of Contents

1. [Who Should Contribute](#who-should-contribute)
2. [What to Contribute](#what-to-contribute)
3. [Prerequisites](#prerequisites)
4. [Development Setup](#development-setup)
5. [Contribution Types & Workflow](#contribution-types--workflow)
6. [Coding & Writing Standards](#coding--writing-standards)
7. [Commit Message Convention](#commit-message-convention)
8. [Pull Request Checklist](#pull-request-checklist)
9. [First Contribution Guide](#first-contribution-guide)

---

## Who Should Contribute

This project is for **senior engineers and AI practitioners** who:
- Work daily with AI coding agents (Cursor, Gemini, Claude, Copilot)
- Have strong opinions about architectural standards and code quality
- Want to codify their expertise into enforceable, reusable rules

---

## What to Contribute

| Contribution Type | Location | Example |
|---|---|---|
| New tech-stack rules | `tech-stack/` | `nuxt-4.md`, `bun-1.md`, `drizzle-orm.md` |
| New behavioral examples | `EXAMPLES.md` | ❌ vs ✅ patterns for a new anti-pattern |
| New workflow protocol | `workflows/` | `09-ai-review.md` for AI-to-AI review loops |
| New global rule | `rules/` | `mobile-standards.md` for React Native |
| Bug fix / correction | Any file | Fix a factual error, broken cross-reference |
| CHANGELOG update | `CHANGELOG.md` | Document your changes properly |

> [!NOTE]
> The most valuable contributions are **tech-stack rule files** for widely-used frameworks and **EXAMPLES.md additions** that demonstrate real anti-patterns with clear ❌ vs ✅ code.

---

## Prerequisites

- Git (2.40+)
- PowerShell 7+ (for running the validation script on Windows)
- A text editor with Markdown preview
- Familiarity with the framework/tech you're writing rules for

---

## Development Setup

```bash
# 1. Fork the repository on GitHub

# 2. Clone your fork
git clone https://github.com/<YOUR_USERNAME>/ai-globals.git
cd ai-globals

# 3. Create a feature branch (see naming conventions below)
git checkout -b feat/tech-stack-nuxt-4

# 4. Make your changes

# 5. Run the validation script to verify integrity
.\scripts\validate-globals.ps1

# 6. If any issues are found, run auto-fix
.\scripts\validate-globals.ps1 -Fix

# 7. Commit and push
git push origin feat/tech-stack-nuxt-4

# 8. Open a Pull Request
```

---

## Contribution Types & Workflow

### Adding a Tech-Stack Rule File (`tech-stack/`)

1. **Name the file** using the format: `{tech}-{major-version}.md` (e.g., `nuxt-4.md`, `bun-1.md`).
2. **Use this structure:**

```markdown
# [Tech Name] [Version] — Standards

> **Version:** X.Y | **Status:** Stable | **Last Verified:** YYYY-MM

## Core Standards
- ...

## Anti-Patterns (Forbidden)
- ...

## Performance Mandates
- ...
```

3. If the tech is **unreleased/preview**, add `[!SPECULATIVE]` header and the tag to `global-workflow.md`.
4. **Log it** in `CHANGELOG.md` under the next version.

### Adding an EXAMPLES.md Entry

Each example must follow this exact template:

```markdown
### Example N: [Short Description]

**User Request:** "[Realistic user request]"

**❌ What LLMs Do (Wrong)**
[Code block showing the anti-pattern]

**Problems:**
- [Specific problem 1]
- [Specific problem 2]

**✅ What Should Happen (Correct)**
[Code block or text showing the correct approach]
```

### Updating a Global Rule (`rules/`)

- **Always** cross-reference the updated rule in `CHANGELOG.md`.
- If the rule creates a conflict with another rule, document the resolution explicitly.
- Run `.\scripts\validate-globals.ps1` to check cross-references are intact.

---

## Coding & Writing Standards

### Markdown Formatting
- Use UTF-8 encoding, LF line endings (enforced by `.editorconfig`)
- Maximum line length: 120 characters for prose, no limit for code blocks
- Use `>` blockquotes sparingly — only for critical architectural notes
- Use `> [!NOTE]`, `> [!IMPORTANT]`, `> [!WARNING]` GitHub alerts for structured callouts
- Every code block must specify a language identifier (` ```php `, ` ```bash `, etc.)

### Content Quality Gates
- **Accuracy:** Every standard must be verified against official documentation
- **Specificity:** Avoid vague statements like "use best practices". State the exact rule.
- **Examples:** Every new rule should have a concrete ❌/✅ example
- **No Bloat:** Each file should be as short as it can be while still being complete

---

## Commit Message Convention

This project follows [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short summary>

[optional body]

[optional footer]
```

| Type | When to Use |
|---|---|
| `feat` | New tech-stack file, new workflow, new rule |
| `fix` | Correcting a factual error or broken reference |
| `refactor` | Restructuring content without changing meaning |
| `docs` | README, CONTRIBUTING, or general documentation |
| `chore` | Validation script, .gitignore, .editorconfig changes |

**Examples:**
```
feat(tech-stack): add nuxt-4.md with SSR and hybrid rendering standards
fix(rules): correct $guarded policy conflict in security-standards.md
refactor(examples): add Laravel 12 architectural decision examples to section 5
```

---

## Pull Request Checklist

Before submitting, confirm all items:

```
[ ] I ran .\scripts\validate-globals.ps1 and all checks pass
[ ] My changes follow the Markdown formatting standards above
[ ] I updated CHANGELOG.md with my changes under the next version
[ ] Every new rule or standard has a concrete code example
[ ] I did NOT include personal project-specific information
[ ] Cross-references to other files use correct section notation (§N)
[ ] Tech-stack files use the correct naming convention
[ ] Speculative/unreleased versions are marked [!SPECULATIVE]
```

---

## First Contribution Guide

**Not sure where to start?** Here's the fastest path to your first meaningful PR:

1. **Look at existing tech-stack files** — pick a framework you know well and check if it's missing or outdated.
2. **Read `EXAMPLES.md`** — think of an AI anti-pattern you've personally encountered that isn't covered yet.
3. **Check open Issues** — look for issues tagged `help-wanted` or `good-first-issue`.

> [!TIP]
> The best first contribution is a **tech-stack rule file** for a framework you use daily. You already know the correct patterns — just codify them.

---

*Questions? Open a [Discussion](https://github.com/m3taz-ahmed/ai-globals/discussions) or [Issue](https://github.com/m3taz-ahmed/ai-globals/issues).*
