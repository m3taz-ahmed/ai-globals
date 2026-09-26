---
name: context-compressor
description: Compress and manage context for LLM sessions.
---
[SKILL] context-compressor
[OBJ] Convert human-readable markdown to Telegraphic Pseudo-Code.
[RULES]
1. [REQ] Trigger: User request or uncompiled file detection.
2. [REQ] Logic Extraction: Analyze core constraints and architecture rules.
3. [REQ] Telegraphic Conversion: Remove grammar, stop words, and conversational prose. Use symbols (`=`, `>`, `&`, `->`) and abbreviations (`Req`, `DB`).
4. [REQ] Output Format: `[CategoryName] RuleName:Condition=Action;`
5. [REQ] Save: Overwrite file directly in its original path.
6. [REQ] Loss budget: preserve semantics over brevity — a compressed rule that dropped its condition or its prohibition is a bug. Numbers, version pins, scope limits, and negations are load-bearing: they survive compression.
7. [REQ] Hierarchy retention: keep section structure (`[SKILL]`/`[RULES]`/etc.) — compression targets prose density, never document skeleton or frontmatter.
8. [REQ] Fidelity check: after compressing, spot-verify 3 rules by expanding them back mentally — if meaning drifted, restore the lossless form for that rule.
9. [REQ] Context hygiene in sessions: when conversation grows long, compress tool outputs and code reads to facts+paths+decisions; never compress requirements, constraints, or user preferences — those stay verbatim.
10. [PROHIBIT] Compressing away conditions (`when X`), prohibitions (`never Y`), or numeric thresholds; re-encoding references (file paths, IDs, library names must stay exact); or compressing code blocks/examples that serve as the only source of truth.
