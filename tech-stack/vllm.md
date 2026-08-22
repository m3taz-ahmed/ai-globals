[TECH] vLLM
[OBJ] High-throughput LLM serving engine using PagedAttention, continuous batching, tensor parallelism, and an OpenAI-compatible API server.
[RULES]
1. [REQ] Install with `pip install vllm` (>=0.6.0); requires CUDA 12.1+ and Python 3.9+ — vLLM does not support CPU-only or AMD ROCm without special builds.
2. [REQ] Launch the OpenAI-compatible server with `vllm serve <model>` or `python -m vllm.entrypoints.openai.api_server --model <model>`; always specify `--host` and `--port` explicitly.
3. [REQ] Set `--tensor-parallel-size N` for multi-GPU serving where N equals the number of GPUs; ensure N divides the model's attention head count evenly.
4. [REQ] Set `--gpu-memory-utilization` (default 0.9) based on available VRAM; reduce to 0.7-0.8 when sharing the GPU with other processes to avoid OOM errors.
5. [REQ] Set `--max-model-len` to control the maximum sequence length; lower this to reduce KV cache memory allocation for models with large nominal context windows (e.g., 128K).
6. [REQ] Use `--enable-prefix-caching` to cache KV for shared prompt prefixes (system prompts, few-shot examples); this dramatically reduces TTFT for repetitive workloads.
7. [REQ] Use `--quantization` (`awq`, `gptq`, `bitsandbytes`, `fp8`) for quantized model serving; ensure the quantization format matches the checkpoint format.
8. [REQ] Use the `LLM` class for offline batch inference (`from vllm import LLM, SamplingParams`); use the server for online serving — do not mix the two in the same process.
9. [REQ] Use `SamplingParams(temperature, top_p, max_tokens, stop)` for generation control; pass `n` for multiple completions and `best_of` for best-of-n sampling.
10. [REQ] Monitor GPU memory, queue depth, and throughput via the `/metrics` Prometheus endpoint; set alerts for OOM risk and request queue buildup.
11. [REQ] Use `--served-model-name` to expose a custom model name in the API; useful when serving fine-tuned checkpoints under a friendly alias.
12. [CMD] `pip install vllm` to install the engine and server.
13. [CMD] `vllm serve meta-llama/Llama-3.3-70B-Instruct --tensor-parallel-size 4 --max-model-len 32768` to serve a 70B model across 4 GPUs.
14. [PROHIBIT] Never run vLLM without `--max-model-len` set explicitly for large-context models; the default will attempt to allocate the full context window in KV cache and OOM.
15. [PROHIBIT] Never expose the vLLM server directly to the internet without an auth proxy; the OpenAI-compatible endpoint has no built-in authentication or rate limiting.
[COMPAT]
- vLLM: >=0.6.0 (Python 3.9+, CUDA 12.1+, Linux only)
- OpenAI-compatible API: /v1/chat/completions, /v1/completions, /v1/embeddings
- Hardware: NVIDIA GPUs (Ampere, Hopper, Ada Lovelace); no CPU inference
[REFS]
- https://docs.vllm.ai/
- https://docs.vllm.ai/en/stable/serving/openai_compatible_server.html
- https://docs.vllm.ai/en/stable/engine/llm_engine.html
- https://github.com/vllm-project/vllm
