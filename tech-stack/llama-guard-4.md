[TECH] Meta Llama Guard 4
[OBJ] Meta Llama Guard 4 (12B) — multimodal text+image safety classifier. 14 hazard categories. Llama Prompt Guard 2 for injection detection. MIT base. Self-hostable.
[RULES]
1. [REQ] Use Llama Guard 4 (12B) for content safety classification: input = text and/or image, output = `safe` / `unsafe` + violated categories. Multimodal — handles text+image jointly.
2. [REQ] Use 14 hazard categories (S1-S14): violence, sexual content, firearms, regulated substances, PII, hate, harassment, self-harm, etc. Configure subset via `custom_categories` in prompt.
3. [REQ] Use Llama Prompt Guard 2 for prompt injection detection: classifies input as `BENIGN` / `INJECTION` / `JAILBREAK`. Deploy as input filter before LLM call.
4. [REQ] Self-host via HuggingFace Transformers: `from transformers import AutoModelForCausalLM, AutoTokenizer`. `model = AutoModelForCausalLM.from_pretrained("meta-llama/Llama-Guard-4-12B")`.
5. [REQ] Use vLLM / TGI for production serving: `vllm serve meta-llama/Llama-Guard-4-12B --tensor-parallel-size 1`. Higher throughput than raw Transformers.
6. [REQ] Use structured prompt format: `<|begin_of_text|>[INST] Task: Check if there is unsafe content in... [/INST]`. Parse `unsafe\nS1,S3` output format.
7. [REQ] Use as output filter: pass LLM response through Llama Guard before returning to user. Block if `unsafe`.
8. [REQ] Use as input filter: pass user input through Llama Guard before LLM call. Reject if `unsafe`.
9. [REQ] Use custom categories for domain-specific safety: define in prompt `Custom Categories: S1: ... S2: ...`. Model adapts to custom taxonomy.
10. [REQ] Use Llama Prompt Guard 2 separately from Llama Guard 4: Prompt Guard = injection detection (input only), Guard 4 = content safety (input + output). Deploy both for defense-in-depth.
11. [REQ] Use quantization (GPTQ/AWQ/GGUF) for deployment on smaller GPUs: 12B fits in ~8GB VRAM with 4-bit quant. `model = AutoModelForCausalLM.from_pretrained(..., load_in_4bit=True)`.
12. [REQ] Use batch inference for throughput: `model.generate(input_ids_batch, max_new_tokens=100)`. Batch multiple safety checks.
13. [REQ] Use `llama-guard` Python helper or direct Transformers API. Configure `max_new_tokens=100` (sufficient for safe/unsafe + categories).
14. [REQ] Use NVIDIA NIM / Together AI / Fireworks for managed hosting if self-hosting not feasible. API-compatible endpoints.
15. [REQ] MIT license for base model — commercial use permitted. Check Llama Community License for fine-tuned variants.
16. [CMD] `pip install transformers accelerate vllm` install serving deps.
17. [CMD] `vllm serve meta-llama/Llama-Guard-4-12B` serve via vLLM.
18. [CMD] `huggingface-cli download meta-llama/Llama-Guard-4-12B` download model weights.
19. [PROHIBIT] Never deploy LLM apps without safety classification in production — use Llama Guard or equivalent.
20. [PROHIBIT] Never use Llama Guard as sole safety layer — combine with Prompt Guard (injection) + output filtering + human review for high-risk.
21. [PROHIBIT] Never fine-tune and redistribute without checking Llama Community License terms.
22. [PROHIBIT] Never run 12B unquantized on <24GB VRAM — use 4-bit/8-bit quantization.
[COMPAT]
- Meta Llama Guard 4 (12B params).
- Llama Prompt Guard 2 (injection detection, separate model).
- MIT base license (check Llama Community License for variants).
- Serving: vLLM, TGI, Transformers, NVIDIA NIM, Together AI, Fireworks.
- Quantization: GPTQ, AWQ, GGUF (4-bit fits ~8GB VRAM).
- Python 3.10+ (3.14 compatible).
[REFS]
- https://huggingface.co/meta-llama/Llama-Guard-4-12B
- https://huggingface.co/meta-llama/Prompt-Guard-2
- https://ai.meta.com/blog/llama-guard-4/
- https://github.com/meta-llama/PurpleLlama
