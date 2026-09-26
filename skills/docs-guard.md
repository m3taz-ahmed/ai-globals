---
name: docs-guard
description: Guard documentation quality and completeness.
---
[SKILL] docs-guard
[OBJ] Verify documentation accuracy against source code.
[RULES]
1. [REQ] Verify Everything: Every referenced function/endpoint/flag MUST exist in code. Do not hallucinate.
2. [REQ] Working Samples: Code samples must have correct signatures.
3. [REQ] Code is Truth: Document actual behavior. If docs conflict with code, flag the code.
4. [PROHIBIT] Unverifiable Claims: No "Fast" or "Production-ready" without repo benchmarks.
5. [REQ] Sync: Function name changes require doc updates.
6. [PROHIBIT] Filler: Delete docstrings that just paraphrase the signature.
7. [REQ] Failure Paths: Document error states, not just happy paths.
8. [REQ] Command reality-check: every shell command, env var, config key, and file path in docs is executed/verified against the repo — pasted-from-memory commands drift within weeks.
9. [REQ] Version alignment: docs must state which version they cover; features documented must exist in the version the lockfile pins — flag docs describing unreleased or removed APIs.
10. [REQ] Link integrity: internal links resolve, anchors exist, external links alive; cross-references updated when pages move — broken links are broken trust.
11. [REQ] Diff-aware review: on PRs, docs are checked against THE DIFF not the whole codebase — new/changed public surface requires doc coverage; removed surface requires doc removal (stale docs about dead features are worse than gaps).
12. [REQ] Audience fit: README gets a 30-second orientation (what/why/install/run); API reference is exhaustive; guides teach workflows. Flag enterprise docs in the README and missing error/limits tables in references.
13. [REQ] Freshness signals: version-pinned screenshots, "last verified" discipline, changelog entries for behavior changes; undocumented changes get blocked at review.
14. [PROHIBIT] Approving docs that describe aspirational (planned) behavior as current, copy-pasted docs from other projects/features without adaptation, or TODO-stub documentation presented as complete.
