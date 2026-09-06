[TECH] Garak (open-source)
[OBJ] LLM vulnerability scanner — probes for multiple attack categories (prompt injection, data leakage, hallucination, bias). Use for automated red-teaming in CI.
[RULES]
1. [REQ] Use Garak for automated LLM vulnerability scanning — probes for prompt injection, data leakage, hallucination, bias, jailbreaks, encoding attacks.
2. [REQ] Run Garak in CI pipelines as automated red-teaming gate — `garak --model_type openai --model_name gpt-4 --probes all`.
3. [REQ] Use probe categories: `promptinject`, `leakage`, `hallucination`, `bias`, `jailbreak`, `encoding`, `continuation`, `goodcode`, `latentinjection`, `maliciousgen`.
4. [REQ] Configure probes selectively — `--probes promptinject,jailbreak` for targeted scans vs `--probes all` for comprehensive.
5. [REQ] Use `--report_type json` for CI-parseable output — parse results, fail build on threshold.
6. [REQ] Use Garak with multiple model backends: OpenAI, HuggingFace, Anthropic, local, custom.
7. [REQ] Use `garak --eval_threshold` to set pass/fail threshold for vulnerability scores.
8. [REQ] Review Garak reports for each model/prompt change — track vulnerability regressions.
9. [REQ] Use Garak alongside Promptfoo — Garak for vulnerability scanning, Promptfoo for eval quality.
10. [REQ] Open-source — check license before commercial integration.
11. [PROHIBIT] Never deploy LLM apps without Garak red-team scan in CI.
12. [PROHIBIT] Never ignore high-severity Garak findings — remediate before deploy.
13. [PROHIBIT] Never run `--probes all` on production endpoints — use staging/test models.
14. [PROHIBIT] Never use Garak as sole quality gate — combine with Promptfoo evals.
15. [CMD] `pip install garak` — install.
16. [CMD] `garak --model_type openai --model_name gpt-4 --probes all` — full scan.
17. [CMD] `garak --model_type openai --model_name gpt-4 --probes promptinject,jailbreak` — targeted scan.
18. [CMD] `garak --model_type openai --model_name gpt-4 --probes all --report_type json` — CI output.
19. [CMD] `garak --list_probes` — list available probes.
20. [CMD] `garak --list_detectors` — list available detectors.
[COMPAT]
- Garak: open-source.
- Python 3.10+.
- Model backends: OpenAI, HuggingFace, Anthropic, local, custom.
- CI integration: JSON report output.
- Complements Promptfoo (evals) + Guardrails AI (validation).
[REFS]
- https://github.com/leondz/garak
- https://garak.readthedocs.io/
- https://github.com/leondz/garak/wiki
