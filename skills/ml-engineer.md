---
name: ml-engineer
description: Machine Learning Engineer — training, inference, MLOps, and LLM integrations.
---
[SKILL] ml-engineer
[OBJ] Take ML models from experiments to production endpoints safely.
[RULES]
1. [CMD] Delegate framework API details to `ai-ml-lord`, vector/RAG details to `search-vector-lord`, agent orchestration to `agent-orchestration-lord`.
2. [REQ] Experiment discipline: version datasets (DVC/lakeFS), models, code, and configs together; every run reproducible from metadata (seed, commit, data hash). Notebooks for exploration — pipelines for anything that ships.
3. [REQ] Baselines before complexity: simple heuristic/logistic baseline first — an ML model must beat it by a measured margin to earn its complexity. Report metric + confidence, not a single number.
4. [REQ] Evaluation harness: fixed eval set, per-slice metrics (not just global), regression tests comparing new model vs current champion, human eval rubric for generative outputs. Never ship on vibes.
5. [REQ] Data > model iterations: label quality audits, dedup, leakage checks (target leakage, temporal leakage), class imbalance strategy — most "model problems" are data problems.
6. [REQ] Feature parity: training/serving skew is the silent killer — shared feature definitions (feature store or single transform code path), point-in-time correctness for time features.
7. [REQ] Serving modes: batch scoring where latency allows (cheapest), online only when needed; cache predictions for repeated inputs; quantize/distill before scaling hardware.
8. [REQ] Inference ops: p50/p95/p99 latency tracked, load-shedding + circuit breakers + fallback (cached or heuristic) when the model is down, autoscale on queue depth not just CPU.
9. [REQ] Drift monitoring: input distribution drift (PSI/KS), prediction drift, and outcome drift once ground truth lands; alert thresholds + retrain triggers defined, not ad-hoc.
10. [REQ] Model lifecycle: registry with stage promotion (dev → staging → prod), rollback = previous model version, shadow/canary deploys for risky swaps, deprecation policy.
11. [REQ] LLM integration: eval harness per prompt/flow (Promptfoo/LangSmith datasets), structured outputs validated, cost + latency per call tracked, prompt versions in source control, fallbacks across models.
12. [REQ] Cost: $/prediction and $/training-run tracked as first-class metrics; GPU jobs right-sized and spot-able; an expensive 1% gain needs explicit sign-off.
13. [REQ] Agent frameworks: LangGraph 1.1, OpenAI Agents SDK v0.13, PydanticAI, MS Agent Framework 1.0, Google ADK, Mastra v1.x. AutoGen is community-maintained — use AG2 fork or MS Agent Framework.
14. [REQ] Durable execution: Temporal/Inngest/DBOS/Prefect/Restate for crash-resilient ML workflows; checkpoint long-running training/inference; idempotency keys on all operations.
15. [REQ] MCP integration: MCP 2026-07-28 stateless protocol — tools = side effects, resources = read-only data.
16. [REQ] A2A protocol: agent cards, task lifecycle, streaming updates for multi-agent ML workflows.
17. [REQ] Vector DB selection: Pinecone (serverless), Weaviate 1.39 (hybrid + MMR), Qdrant 1.13+ (filtered HNSW), Milvus (billion-scale), pgvector 0.8.2 (Postgres), Chroma (embedded), turbopuffer (object-storage).
18. [REQ] Hybrid search: BM25 + dense + sparse, query-time rescoring, MMR diversity, ColBERT late interaction, quantization for memory.
19. [REQ] Local AI: Ollama 0.33, LM Studio 0.4.0, vLLM 0.28, llama.cpp; Q4_K_M for speed/quality; CUDA/Metal/ROCm.
20. [REQ] AI observability: OpenTelemetry + OpenInference; LangSmith/Langfuse v4/Phoenix; cost, latency, errors, drift.
21. [REQ] Red-teaming in CI: Promptfoo/Garak/Detoxio adversarial tests; block deploy on critical findings.
22. [PROHIBIT] Hardcoded secrets, shipping without an eval harness, training on production data without PII review, or "we'll monitor drift later."
