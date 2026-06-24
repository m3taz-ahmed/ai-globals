# AI OS Rules Architecture

This directory contains **compressed behavioral and structural rules** for AI Global OS. All files use Telegraphic Pseudo-Code (`[FILE]/[RULES]` format) — natively dense, no compilation step required.

## Loading Protocol

Rules load lazily per `global-workflow.md`:

| Layer | Files | When |
|---|---|---|
| Layer 0 | `core-behavioral-compact.md` | Every session |
| Layer 1 | `vocabulary.md`, `anti-patterns.md` | Every session |
| Layer 2 | All other `rules/*.md` | On-demand |

**Vocabulary** (`rules/vocabulary.md`) is the sole definition source for all symbolic codes (`[BEH-xx]`, `[SEC-xx]`, etc.). Load it before referencing any code.

## Files

| File | Purpose |
|---|---|
| `vocabulary.md` | Canonical symbolic code dictionary |
| `core-behavioral-compact.md` | Minimum viable behavioral constraints |
| `anti-patterns.md` | Prohibited patterns and LLM failure modes |
| `principal-architect.md` | Architectural identity and authority |
| `llm-behavioral-guidelines.md` | AI response quality gates |
| `ai-integration-standards.md` | Agentic/LLM integration rules |
| `persistent-state-execution.md` | Multi-step task state management |
| `spec-cache.md` | Project spec caching protocol |
| `EXAMPLES.md` | Concrete ❌/✅ pattern examples |

## Format

All AI-loaded files follow:
```
[FILE] name
[OBJ] Single-sentence objective.
[RULES]
1. [REQ|CMD|PROHIBIT] Rule body.
```

Human docs (`README.md`) use standard Markdown.
