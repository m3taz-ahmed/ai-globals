[TECH] Hugging Face Diffusers
[OBJ] Python library for state-of-the-art diffusion models including Stable Diffusion, FLUX, ControlNet, img2img, inpainting, LoRA, and pipeline customization.
[RULES]
1. [REQ] Install with `pip install diffusers transformers accelerate` (>=0.31.0); include `peft` for LoRA support and `safetensors` for secure model loading.
2. [REQ] Load pipelines with `from diffusers import DiffusionPipeline; pipe = DiffusionPipeline.from_pretrained(model_id, torch_dtype=torch.float16)`; use `variant="fp16"` when available to download half-precision weights directly.
3. [REQ] Move pipelines to GPU with `pipe.to("cuda")` before inference; for multi-GPU, use `device_map="balanced"` with `enable_model_cpu_offload()` for memory-constrained setups.
4. [REQ] Use `pipe.enable_xformers_memory_efficient_attention()` or `pipe.enable_attention_slicing()` to reduce VRAM usage for large models on consumer GPUs; verify xformers is installed.
5. [REQ] For FLUX models, use `FluxPipeline` or `FluxTransformer2DModel` with `torch_dtype=torch.bfloat16`; FLUX requires significant VRAM (24GB+ for full, 12GB+ for quantized/schnell).
6. [REQ] For ControlNet, load with `ControlNetModel.from_pretrained(controlnet_id)` and pass to `StableDiffusionControlNetPipeline(pipe, controlnet=controlnet)`; always provide conditioning images matching the ControlNet type (Canny, Depth, Pose, etc.).
7. [REQ] For img2img, use `StableDiffusionImg2ImgPipeline` with `image` and `strength` parameters (0.3-0.8 range); `strength` controls how much the original image is altered.
8. [REQ] For inpainting, use `StableDiffusionInpaintPipeline` with `image`, `mask_image`, and `prompt`; ensure mask is a binary PIL Image where white (255) = area to inpaint.
9. [REQ] Load LoRA weights with `pipe.load_lora_weights(lora_path)` and adjust strength with `pipe.set_adapters(adapter_names, adapter_weights=[0.8])`; unload with `pipe.unload_lora_weights()` when switching tasks.
10. [REQ] Use `pipe.fuse_lora()` after loading to merge LoRA weights into the base model for zero-overhead inference; call `pipe.unfuse_lora()` before loading a different LoRA.
11. [REQ] Set a fixed `generator = torch.Generator("cuda").manual_seed(seed)` for reproducible generation; never rely on default seeding for production outputs.
12. [CMD] `pip install diffusers transformers accelerate peft safetensors xformers` to install the full diffusion stack.
13. [CMD] `pipe = DiffusionPipeline.from_pretrained("black-forest-labs/FLUX.1-schnell", torch_dtype=torch.bfloat16)` to load FLUX schnell.
14. [PROHIBIT] Never use `torch.float32` for diffusion inference on GPU; always use `float16` or `bfloat16` — float32 doubles VRAM usage with negligible quality difference.
15. [PROHIBIT] Never call `pipe.to("cuda")` after `enable_model_cpu_offload()` — the latter manages device placement automatically; manual `.to()` will conflict and cause OOM or errors.
[COMPAT]
- Python: diffusers>=0.31.0 (Python 3.9+)
- Dependencies: torch>=2.1.0, transformers>=4.40.0, accelerate>=0.30.0, peft>=0.12.0
- Models: FLUX.1-dev/schnell, SDXL, SD3.5, Stable Diffusion 1.5/2.1
[REFS]
- https://huggingface.co/docs/diffusers
- https://huggingface.co/docs/diffusers/en/using-diffusers/loading_overview
- https://huggingface.co/docs/diffusers/en/using-diffusers/controlnet
- https://huggingface.co/docs/diffusers/en/using-diffusers/loading_adapters
