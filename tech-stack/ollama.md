[TECH] Ollama
[OBJ] Local LLM runtime for running open-weight models with model management, an OpenAI-compatible API, Modelfile customization, quantization, and GPU acceleration.
[RULES]
1. [REQ] Install Ollama from the official installer (`ollama.com` or `curl -fsSL https://ollama.com/install.sh | sh` on Linux); verify with `ollama --version` before use.
2. [REQ] Pull models with `ollama pull <model>` (e.g., `ollama pull llama3.3:70b`, `ollama pull qwen2.5:14b`); always pin a specific tag rather than `latest` in production for reproducibility.
3. [REQ] Use the OpenAI-compatible endpoint at `http://localhost:11434/v1` with `base_url` override in the OpenAI SDK for drop-in compatibility with existing toolchains.
4. [REQ] Use the native Ollama API (`POST /api/chat` or `/api/generate`) for features not covered by the OpenAI shim, such as `keep_alive` to control model unloading from memory.
5. [REQ] Set `OLLAMA_HOST` environment variable to bind to a non-default interface (e.g., `OLLAMA_HOST=0.0.0.0:11434` for network access); never expose port 11434 to the public internet without a reverse proxy with authentication.
6. [REQ] Create custom models with a `Modelfile` (`FROM <base>`, `PARAMETER temperature 0.7`, `SYSTEM "..."`, `TEMPLATE "..."`); build with `ollama create <name> -f Modelfile`.
7. [REQ] Use quantized models (e.g., `:Q4_K_M`, `:Q5_K_M`) for memory-constrained environments; prefer Q4_K_M for the best speed/quality trade-off on consumer GPUs.
8. [REQ] Configure GPU acceleration via `OLLAMA_GPU_OVERHEAD` and ensure CUDA (Linux/Windows) or Metal (macOS) is detected; verify with `ollama ps` which shows GPU/CPU placement.
9. [REQ] Use `ollama run <model>` for interactive CLI chat; use the HTTP API or SDK for programmatic access in applications.
10. [REQ] Manage model lifecycle with `ollama list`, `ollama rm <model>` (frees disk), and `ollama cp <src> <dst>`; periodically prune unused models to reclaim storage.
11. [REQ] Set `num_ctx` in the Modelfile or API request to control context window size; default is 2048 which is often too small — increase to 8192 or 32768 for RAG workloads.
12. [CMD] `ollama serve` to start the Ollama daemon (runs automatically on macOS/Windows app launch; required manually on Linux without systemd).
13. [CMD] `ollama show <model> --modelfile` to inspect a model's configuration and parameters.
14. [PROHIBIT] Never run Ollama bound to `0.0.0.0` without firewall rules or a reverse proxy with auth; the API has no built-in authentication and allows arbitrary model execution.
15. [PROHIBIT] Never assume a model fits in VRAM without checking `ollama ps` for offload status; CPU fallback severely degrades latency for large models.
[COMPAT]
- Ollama: >=0.5.0 (Linux, macOS, Windows)
- OpenAI-compatible API: /v1/chat/completions, /v1/embeddings, /v1/models
- Models: llama3.3, qwen2.5, deepseek-r1, mistral, phi4, gemma2
[REFS]
- https://ollama.com/
- https://github.com/ollama/ollama/blob/main/docs/api
- https://ollama.com/blog/openai-compatibility
- https://github.com/ollama/ollama/blob/main/docs/modelfile
