[TECH] Promptfoo (acquired by OpenAI, Mar 2026)
[OBJ] LLM evaluation + red-teaming + CI integration — evals, red-team tests, CI-integrated eval gates. MIT license. Now owned by OpenAI.
[RULES]
1. [REQ] Use Promptfoo for red-teaming + evals + CI integration — red-team tests, eval suites, CI-integrated eval gates.
2. [REQ] Use red-teaming for prompt injection, jailbreaks, data leakage, bias, toxicity probes — `promptfoo redteam run`.
3. [REQ] Use eval suites (`promptfooconfig.yaml`) to define test cases, assertions, prompts, models — run `promptfoo eval`.
4. [REQ] Integrate eval gates in CI — fail builds on assertion failures or score regressions.
5. [REQ] Use assertion types: `contains`, `icontains`, `regex`, `javascript`, `python`, `model-graded-closed`, `rubric`, `similar`, `webfetch`.
6. [REQ] Use `model-graded-closed` / `rubric` assertions for LLM-as-judge evaluation.
7. [REQ] Use `promptfoo view` to review eval results in web UI.
8. [REQ] Use `promptfoo compare` to compare eval runs across prompt/model versions.
9. [REQ] Note: Promptfoo acquired by OpenAI (Mar 2026) — still MIT licensed; monitor for license/policy changes.
10. [REQ] Use `promptfoo generate test` to auto-generate test cases from prompts.
11. [REQ] Use matrix testing — test multiple prompts × models × test cases in one config.
12. [PROHIBIT] Never deploy prompt changes without running eval suite in CI.
13. [PROHIBIT] Never use only `contains`/`regex` assertions for complex outputs — use `model-graded-closed` or `rubric`.
14. [PROHIBIT] Never skip red-team tests for production-facing LLM apps.
15. [PROHIBIT] Never assume OpenAI acquisition means OpenAI-only — still supports multi-provider.
16. [CMD] `npx promptfoo init` — scaffold config.
17. [CMD] `npx promptfoo eval` — run eval suite.
18. [CMD] `npx promptfoo redteam run` — run red-team tests.
19. [CMD] `npx promptfoo view` — web UI for results.
20. [CMD] `npx promptfoo compare` — compare eval runs.
[COMPAT]
- Promptfoo: MIT license (post-OpenAI acquisition).
- Acquired by OpenAI Mar 2026 — monitor for changes.
- Multi-provider: OpenAI, Anthropic, Google, local models, etc.
- Node.js / npx based.
- CI integration: GitHub Actions, GitLab CI, etc.
[REFS]
- https://www.promptfoo.dev/
- https://github.com/promptfoo/promptfoo
- https://www.promptfoo.dev/docs/red-team/
- https://www.promptfoo.dev/docs/usage/
