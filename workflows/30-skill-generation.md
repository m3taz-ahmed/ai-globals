---
name: skill-generation
trigger: generate skill, create skill from book, convert document to skill, book to skill, skill from pdf, skill from doc
persona: ARCH
engine: runtime/skill_eval.py
---

# Skill Generation Pipeline

Convert books, documents, RFCs, wikis, and PDFs into structured aiZee skills. Extract frameworks, mental models, principles, techniques, and anti-patterns — not summaries.

## Philosophy

Documents contain crystallized expertise. This workflow extracts that knowledge into a format aiZee can leverage repeatedly as a skill.

**Extract structure, not summaries.** A skill is a toolkit of:
- Named frameworks (mental models with clear application)
- Actionable principles (rules that guide decisions)
- Techniques (step-by-step methods)
- Anti-patterns (what to avoid and why)
- Voice calibration (how the author thinks and communicates)

**Preserve the author's precision.** Frameworks have specific names for reasons. "The 5 Whys" isn't interchangeable with "ask why multiple times."

**Layer depth appropriately.** Simple docs → simple skills. Complex docs with 10+ frameworks → skills with reference files and on-demand chapters.

## Modes

1. **Full Conversion (default):** Run all steps (0–9). Output: complete skill with SKILL.md, chapters/, glossary, patterns, cheatsheet, EVAL.md.
2. **Analyze Only:** Run steps 0–3, produce extraction report, stop.
3. **Generate from Prior Analysis:** Skip 0–3, use provided analysis, run 4–9.
4. **Update / Fold-in:** Merge new content into existing skill.

## Step 0 — Out-of-scope check

If no document path provided, stop:
> "skill-generation requires a document path. Usage: `aizee workflow skill-generation <path> [skill-name-slug]`"

## Step 1 — Validate input

Verify at least one supported file exists: `.pdf`, `.epub`, `.docx`, `.txt`, `.md`, `.markdown`, `.rst`, `.adoc`, `.html`, `.htm`, `.rtf`.

## Step 1.5 — Identify content type

Ask the user:
> 1. **Technical** — code blocks, tables, formulas, diagrams
> 2. **Text-heavy** — mostly prose
> 3. **Not sure** — fast method with quality warning

Store as `BOOK_TYPE`: `technical` or `text`.

## Step 2 — Extract text

Use `runtime/text_sanitize.py` to sanitize extracted text (strip invisible codepoints for prompt injection defense). Create:
- `<tempdir>/full_text.txt` — combined extracted text
- `<tempdir>/metadata.json` — size, words, pages, token counts

## Step 2.5 — Pre-flight cost estimate

Present token cost estimate before generation:
```
Sources: N | Pages: ~N | Words: ~N | Tokens: ~NK
Input: ~NK | Output: ~NK | Total: ~NK
Estimated cost: $N.NN (at current provider rates)
Proceed? (or "analyze only" to preview)
```

Use `runtime/provider_registry.py` to get current cost rates.

## Step 2.6 — REPL-style access for large docs (>50k tokens)

For docs over 50k tokens, use grep/sed/wc to probe the corpus instead of reading the whole file. Keep generation cost proportional to output, not source.

On Windows, use PowerShell equivalents:
- `Select-String` instead of `grep`
- `Get-Content -TotalCount N` instead of `head -N`
- `(Get-Content file).Count` instead of `wc -l`

## Step 3 — Analyze structure

Read the first 8,000 characters to identify: title, author(s), chapter structure, core themes, approximate chapter count.

**If analyze-only:** produce extraction report and stop.

## Step 4 — Ask purpose

> What should this skill help you do?
> 1. Apply the author's frameworks while working
> 2. Think with the author's mental models
> 3. Reference specific chapters and concepts
> 4. All of the above

Derive `DEPTH`: option 3 only → `reference`; options 1/2/4 → `study`.

## Step 5 — Determine skill name

If provided, use it. Otherwise propose:
- By author-concept: `{author}-{concept}` (e.g. `cialdini-influence`)
- By title: lowercase hyphens (e.g. `designing-data-intensive-apps`)

Destination: `skills/<skill_name>/` under the aiZee root.

## Step 6 — Create directory structure

```
skills/<skill_name>/
├── SKILL.md
├── EVAL.md
├── chapters/
│   ├── ch01-<slug>.md
│   ├── ch02-<slug>.md
│   └── ...
├── references/
│   ├── glossary.md
│   ├── patterns.md
│   └── cheatsheet.md
```

## Step 7 — Generate chapter summaries

**Token budget matrix:**

| | DEPTH=reference | DEPTH=study |
|---|---|---|
| BOOK_TYPE=text | 800–1,200 tokens | 1,000–1,800 tokens |
| BOOK_TYPE=technical | 1,200–1,800 tokens | 2,000–3,000 tokens |

For each chapter, create `chapters/ch<NN>-<slug>.md`:

```markdown
# Chapter N: <Title>

## Core Idea
<1-2 sentences>

## Frameworks Introduced
- **<Name>**: <formulation>
  - When to use: <situation>
  - How: <steps>

## Key Concepts
- **<Term>**: <definition>

## Mental Models
<2-4 frameworks as "Use X when Y">

## Anti-patterns
- **<What to avoid>**: <why>

## Worked Example *(study depth only)*
<reconstructed example>

## Key Takeaways
1. <insight>
```

## Step 8 — Generate glossary, patterns, cheatsheet

- `references/glossary.md` — key terms with definitions
- `references/patterns.md` — recurring patterns and anti-patterns
- `references/cheatsheet.md` — quick-reference card

## Step 9 — Generate SKILL.md + EVAL.md

**SKILL.md** frontmatter:
```yaml
---
name: <skill_name>
description: <one-line description>
triggers: <keywords>
personas: [ARCH, DOC]
tech_stack: [markdown]
---
```

**EVAL.md** — self-checks the skill runs on its own output (see `runtime/skill_eval.py`).

## Quality gate

After generation:
1. Run `runtime/skill_eval.py` to validate the skill against its EVAL.md
2. Run `runtime/text_sanitize.py` on all generated files (defense in depth)
3. Run `aizee memory ingest` to refresh indexes
4. Test with `aizee persona detect --multi "<skill description>"`
