---
name: drafter-reviewer
trigger: draft and review, two-pass generation, critique and revise, drafter reviewer, adversarial review
persona: ARCH
engine: runtime/output_gate.py
---

# Drafter-Reviewer Pipeline

Two-agent pipeline for content generation with adversarial review. The drafter produces a first pass; the reviewer critiques it; the drafter revises based on critique; the final output passes the output gate.

Ported from ai-job-search (MadsLorentzen/ai-job-search) apply workflow pattern.

## When to use

- Content generation where quality matters (skills, docs, proposals, code comments)
- Any output that benefits from a second pass with fresh eyes
- When a single-pass generation is risky (complex topic, high stakes, user-facing)

## Pipeline

### Phase 1: Draft

The drafter agent produces a first draft following the task requirements.

Rules for the drafter:
- Focus on completeness — get all the content down
- Don't optimize for style yet — substance first
- Mark uncertain sections with `[?]` for the reviewer to check
- Follow the relevant skill/workflow for the content type

### Phase 2: Review

The reviewer agent critiques the draft. The reviewer is a separate agent instance (or subagent) that has not seen the drafting process.

Rules for the reviewer:
- Check factual accuracy — every claim must be verifiable
- Check completeness — did the drafter miss anything required?
- Check clarity — can the target audience understand this?
- Check structure — does the flow make sense?
- Check voice — does it match the expected tone?
- Run `runtime/output_gate.py` on the draft
- List specific, actionable findings (not vague feedback)
- Categorize each finding: `BLOCKER` / `WARNING` / `INFO`

Output format from reviewer:
```
## Review Findings

### BLOCKERS
1. [line/section]: <issue> → <fix>

### WARNINGS
1. [line/section]: <issue> → <suggestion>

### INFO
1. [line/section]: <observation>
```

### Phase 3: Revise

The drafter revises based on the review findings.

Rules for the drafter:
- Address every BLOCKER — no exceptions
- Address WARNINGS unless there's a documented reason to skip
- INFO items are optional
- After revising, run `runtime/output_gate.py` on the revised draft
- If any error-severity issues remain, fix and re-check

### Phase 4: Final check

Run the final output through:
1. `runtime/output_gate.py` — pre-send check + portability test
2. `runtime/skill_eval.py` — if the output is a skill, run its EVAL.md
3. `runtime/text_sanitize.py` — strip invisible codepoints (defense in depth)

Only emit the output if all checks pass.

## Subagent orchestration

When using `subagent-driven-development` lord skill:

```
drafter = spawn_subagent(role="drafter", task=<task>)
draft = drafter.execute()

reviewer = spawn_subagent(role="reviewer", task="review this draft", input=draft)
findings = reviewer.execute()

drafter = spawn_subagent(role="drafter", task="revise based on findings", input=draft, critique=findings)
final = drafter.execute()
```

## Quality gate

- All BLOCKER findings addressed
- `output_gate.check_output()` passes (no error-severity issues)
- If skill output: `skill_eval.eval_skill_output()` passes (all checks pass)
- `text_sanitize.sanitize_text()` returns 0 removed codepoints
