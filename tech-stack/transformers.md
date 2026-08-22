[TECH] Hugging Face Transformers
[OBJ] Python library for using and fine-tuning pre-trained transformer models via pipeline API, AutoModel/AutoTokenizer, quantization, and GGUF export.
[RULES]
1. [REQ] Install with `pip install transformers` (>=4.46.0); install `tokenizers`, `accelerate`, and `safetensors` alongside for optimal performance and security.
2. [REQ] Use `AutoTokenizer.from_pretrained(model_id)` and `AutoModelForCausalLM.from_pretrained(model_id)` for model loading; never hardcode model class names (e.g., `LlamaForCausalLM`) unless you need model-specific behavior.
3. [REQ] Always call `tokenizer.apply_chat_template(messages, tokenize=False)` to format chat inputs; never manually concatenate role strings — chat templates are model-specific and critical for correct behavior.
4. [REQ] Use `pipeline("text-generation", model=model_id, device_map="auto")` for quick inference; pass `torch_dtype=torch.bfloat16` to reduce memory and improve speed on Ampere+ GPUs.
5. [REQ] Use `device_map="auto"` (requires `accelerate`) for automatic device placement across multiple GPUs; never manually `.to("cuda")` multi-GPU models.
6. [REQ] Use `BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16)` with `from_pretrained(quantization_config=...)` for 4-bit quantized loading; requires `bitsandbytes` package.
7. [REQ] For fine-tuning, use `Trainer` or `SFTTrainer` (from TRL) with `TrainingArguments`; set `per_device_train_batch_size`, `gradient_accumulation_steps`, and `learning_rate` explicitly — never use defaults for production training.
8. [REQ] Use `DataCollatorForLanguageModeling` or `DataCollatorForSeq2Seq` for batch padding; never pad manually — the collator handles dynamic padding per-batch.
9. [REQ] Save fine-tuned models with `model.save_pretrained(path)` and `tokenizer.save_pretrained(path)`; always save both — a model without its tokenizer is unusable.
10. [REQ] Use `GGUF` export via `llama-cpp-python` or the `convert_hf_to_gguf.py` script from `llama.cpp` for deployment on CPU or edge devices; specify quantization level (e.g., `q4_k_m`) during conversion.
11. [REQ] Set `HF_HOME` or `TRANSFORMERS_CACHE` environment variable to control model cache location; the default `~/.cache/huggingface` can fill disk on large model downloads.
12. [CMD] `pip install transformers accelerate safetensors tokenizers bitsandbytes` to install the full inference stack.
13. [CMD] `huggingface-cli login` to authenticate for gated models (Llama, Mistral, etc.); store token in `HF_TOKEN` env var for CI/CD.
14. [PROHIBIT] Never use `torch.float32` for inference on GPUs; always use `bfloat16` or `float16` to halve memory usage with no quality loss on modern hardware.
15. [PROHIBIT] Never download models at runtime in production; pre-download and pin to a local path or specific revision (`from_pretrained(model_id, revision="...")`) to avoid silent model updates.
[COMPAT]
- Python: transformers>=4.46.0 (Python 3.9+)
- Dependencies: torch>=2.1.0, accelerate>=1.0.0, safetensors>=0.4.0
- Fine-tuning: trl>=0.12.0, peft>=0.13.0
[REFS]
- https://huggingface.co/docs/transformers
- https://huggingface.co/docs/transformers/main/en/quantization
- https://huggingface.co/docs/trl/
- https://github.com/ggerganov/llama.cpp/blob/master/convert_hf_to_gguf.py
