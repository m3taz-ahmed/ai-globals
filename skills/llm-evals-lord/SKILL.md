---
name: llm-evals-lord
description: Lord skill for LLM evaluation — scoring, regression testing, prompt regression, agent evaluation, and production LLM quality monitoring.
triggers:
  - llm eval
  - llm evaluation
  - prompt regression
  - agent eval
  - llm scoring
  - llm quality
  - eval harness
  - تقييم llm
personas:
  - ML
  - AI
  - QA
  - ARCH
  - DEV
tech_stack:
  - transformers
  - langgraph-1
  - openai-agents-sdk
  - google-adk
lord: true
---

# LLM Evals Lord

[OBJ] Evaluate LLM systems — models, prompts, agents, RAG pipelines — using rigorous, reproducible, regression-resistant evaluation methodology.

## Problem

LLM outputs are non-deterministic. Without evals, prompt changes silently degrade quality, model upgrades break behavior, and RAG retrieval failures go undetected. Ad-hoc "vibe checks" don't scale. This skill enforces systematic LLM evaluation: golden datasets, automated scoring, regression gates, and production monitoring.

## Rules

1. [REQ] **Build golden datasets.** Curate 100-500 examples per task with expected outputs. Include edge cases, adversarial inputs, and real production samples. Version datasets (D1, D2, ...) and track metrics per version.
2. [REQ] **Use multiple scoring methods:**
   - **Exact match / F1** — for structured output (JSON, SQL, code)
   - **LLM-as-judge** — GPT-5/Claude-Opus as evaluator with rubric. Use pairwise comparison for ranking.
   - **Embedding similarity** — cosine similarity for semantic equivalence
   - **Human eval** — sample 10-20% for human review, track inter-annotator agreement (Cohen's κ > 0.7)
3. [REQ] **Use `deepeval` or `ragas` frameworks.** `deepeval` for unit-testing LLMs (assertions like `assert_relevancy`, `assert_faithfulness`). `ragas` for RAG pipeline eval (context precision, answer relevance, faithfulness).
4. [REQ] **Track these metrics per eval run:**
   - **Accuracy / correctness** — does output match expected?
   - **Faithfulness** — is output grounded in context (no hallucination)?
   - **Relevancy** — is output relevant to query?
   - **Latency** — p50, p95, p99 response time
   - **Cost** — tokens in/out, $ per request
   - **Safety** — toxicity, PII leakage, jailbreak resistance
5. [REQ] **Run evals in CI/CD.** Block PRs that regress eval scores > 5%. Use `pytest` + `deepeval` or custom harness. Eval runs should be < 5 min for fast feedback.
6. [REQ] **Prompt regression testing.** Version prompts (P1, P2, ...). Run all prompts against golden dataset on every change. Track metric deltas per prompt version.
7. [REQ] **Agent evaluation.** For multi-step agents, evaluate:
   - **Tool selection accuracy** — did agent pick the right tool?
   - **Tool call correctness** — were arguments valid?
   - **Task completion** — did agent achieve the goal?
   - **Step efficiency** — how many steps to complete?
   - **Recovery** — did agent recover from errors?
8. [REQ] **RAG evaluation.** Evaluate retrieval + generation separately:
   - **Context precision** — are retrieved chunks relevant?
   - **Context recall** — are all needed chunks retrieved?
   - **Answer faithfulness** — is answer grounded in context?
   - **Answer relevancy** — is answer relevant to query?
9. [REQ] **Production monitoring.** Log inputs, outputs, scores, latency, cost. Sample 1-5% for human review. Alert on:
   - Error rate > 1%
   - P95 latency > 2x baseline
   - Faithfulness score < 0.9
   - Cost per day > budget
10. [REQ] **Use A/B testing for model/prompt changes.** Route 10% traffic to candidate, compare metrics over 1000+ requests. Statistical significance (p < 0.05) before full rollout.
11. [REQ] **Use `Braintrust` or `LangSmith` or `Helicone`** for eval tracking, experiment comparison, and production monitoring.
12. [PROHIBIT] Never use LLM-as-judge alone — combine with exact match, human eval, and rule-based checks.
13. [PROHIBIT] Never deploy a prompt change without running evals against golden dataset.
14. [PROHIBIT] Never use production traffic for evals without user consent and PII filtering.

## Commands

- `pip install deepeval ragas` — install eval frameworks
- `pytest tests/eval/ -q` — run eval tests
- `deepeval test run tests/eval/` — run deepeval suite
- `python eval/harness.py` — aiZee eval harness

## References

- https://docs.confident-ai.com/ (deepeval)
- https://docs.ragas.io/ (ragas)
- https://www.braintrust.dev/ (Braintrust)
- https://docs.smith.langchain.com/ (LangSmith)
