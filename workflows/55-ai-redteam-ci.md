# Workflow 55 — AI Red-Teaming in CI

[TRIGGER] red team ci, redteam ci, adversarial test ci, promptfoo ci, garak ci, detoxio ci, فريق أحمر
[PERSONA] SEC, QA, ML, ARCH
[TECH] promptfoo, garak, nemo-guardrails, llama-guard-4

## Objective

Integrate AI red-teaming into CI/CD pipeline. Block deployment on critical vulnerabilities. Measure detection rate and false positive rate. Test against OWASP LLM Top 10 2026 and ASI Top 10 2026.

## Steps

1. **Install red-team tools.** `pip install promptfoo garak guardrails-ai`. Install NeMo Guardrails v0.24 and Llama Guard 4 for classifier-based detection. Install Detoxio for adversarial test generation.

2. **Define attack categories.** Configure test suites for: prompt injection (direct + indirect + cross-modal), jailbreak, data leakage, hallucination, bias, tool abuse, MCP tool poisoning, memory-persistence attacks, excessive agency, supply chain.

3. **OWASP LLM Top 10 2026 coverage.** Map tests to all 10 OWASP LLM 2026 categories: LLM01 Prompt Injection (cross-modal + memory), LLM02 Sensitive Info Disclosure, LLM03 Excessive Agency, LLM04 Supply Chain, LLM05 Data/Model Poisoning, LLM06 Unbounded Consumption, LLM07 Misinformation, LLM08 Hidden Context Exposure, LLM09 Vector/Embedding Weaknesses, LLM10 Improper Output Handling.

4. **OWASP ASI Top 10 2026 coverage.** Map tests to agentic-specific categories: ASI03 Identity & Privilege Abuse, ASI04 Agentic Supply Chain Vulnerabilities, ASI05 Unexpected Code Execution.

5. **Cross-modal attack testing.** Test prompt injection via images, audio, and documents. Untrusted multimodal content must be sandboxed. Use Lakera PINT benchmark for image-based injection.

6. **Memory-persistence attack testing.** Test for hidden instructions that survive across turns. Inject tainted content in one turn, verify it does not affect subsequent turns. Memory stores must be taint-labeled and sanitized.

7. **MCP tool poisoning testing.** Verify tool definitions are hash-pinned and re-validated on every list refresh. Simulate server-side tool definition changes (CVE-2025-54136 pattern). Verify detection.

8. **Benchmark suites.** Use PIArena for multi-turn injection, Lakera PINT for image injection, Garak probes for vulnerability scanning, Promptfoo for custom red-team tests.

9. **Benign case testing.** Run benign prompts alongside adversarial ones. Measure false positive rate. A guardrail that blocks 100% of attacks but also blocks 30% of benign requests = unusable.

10. **CI gate integration.** Add red-team tests to CI pipeline. Block deployment on: critical vulnerability found, detection rate < threshold (e.g., 90%), false positive rate > threshold (e.g., 5%).

11. **Regression testing.** Store adversarial test cases in version control. Run on every change to prompts, guardrails, or agent logic. New failure = regression.

12. **Report generation.** Generate report with: attack category, test case, result (pass/fail), severity, detection method, false positive rate, coverage metrics. Export for compliance evidence.

13. **Continuous improvement.** Review red-team test results weekly. Add new attack patterns. Remove obsolete tests. Update thresholds based on metrics.

14. **Quality gate.** Run `ruff check .`, `mypy`, `aizee test --full`. Run red-team suite. Verify detection rate ≥ 90%, false positive rate ≤ 5%.

15. **Memory sync.** Update `Memory.md` with red-team CI integration milestone. Update `CHANGELOG.md` `[Unreleased]` section.

## References

- `tech-stack/promptfoo.md` — Promptfoo red-teaming
- `tech-stack/garak.md` — Garak vulnerability scanning
- `tech-stack/nemo-guardrails.md` — NeMo Guardrails
- `tech-stack/llama-guard-4.md` — Llama Guard 4
- `skills/ai-redteam-lord/SKILL.md` — AI red-team lord skill
- https://genai.owasp.org/ — OWASP LLM Top 10 2026
