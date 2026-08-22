[TECH] Sentence-Transformers
[OBJ] Python framework for state-of-the-art embedding models, cross-encoders, semantic search, and MTEB benchmark evaluation with quantization support.
[RULES]
1. [REQ] Install with `pip install sentence-transformers` (>=3.3.0); this pulls `transformers`, `torch`, and `huggingface-hub` as dependencies — do not install them separately with conflicting versions.
2. [REQ] Load models with `SentenceTransformer("model_name")` (e.g., `"BAAI/bge-m3"`, `"intfloat/multilingual-e5-large-instruct"`); use `device="cuda"` for GPU inference or let it auto-detect.
3. [REQ] Generate embeddings with `model.encode(sentences, convert_to_tensor=True, normalize_embeddings=True)` for retrieval; always normalize for cosine similarity search.
4. [REQ] Use `util.semantic_search(query_embeddings, corpus_embeddings, top_k=5)` from `sentence_transformers.util` for efficient similarity search; this is faster than manual cosine similarity for large corpora.
5. [REQ] For cross-encoder reranking, use `CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")` with `model.predict(pairs)`; always rerank after initial bi-encoder retrieval for best precision.
6. [REQ] Use instruction-prefixed models (e.g., E5, BGE, GTE) with their required query prefixes (`"query: "`, `"passage: "`); omitting prefixes degrades retrieval quality by 10-20%.
7. [REQ] For production vector search, use `model.encode()` in batch mode (`batch_size=32` or `64`); encode the corpus once and persist to a vector database (FAISS, pgvector, Qdrant) — never re-encode on every query.
8. [REQ] Use `model.quantize()` or load quantized variants for CPU deployment; int8 quantization reduces model size by ~4x with minimal quality loss (check MTEB scores before deploying).
9. [REQ] Evaluate embedding models on MTEB (Massive Text Embedding Benchmark) before deployment; check `https://huggingface.co/spaces/mteb/leaderboard` for current rankings across tasks (retrieval, STS, classification, clustering).
10. [REQ] Use `model.save("path")` to persist a model locally for offline deployment; load with `SentenceTransformer("path")` — avoid downloading from HuggingFace Hub at runtime in production.
11. [REQ] Set `model.max_seq_length` explicitly when working with long documents; default is often 256 or 512 — truncate or chunk longer inputs to avoid silent truncation that loses semantic information.
12. [CMD] `pip install sentence-transformers` to install the library.
13. [CMD] `python -m sentence_transformers.eval_mteb --model_name <model>` to evaluate a model on MTEB tasks.
14. [PROHIBIT] Never compare embeddings from different models with cosine similarity — embedding spaces are model-specific; mixing models produces meaningless similarity scores.
15. [PROHIBIT] Never use a bi-encoder (embedding model) for final reranking without a cross-encoder; bi-encoders trade precision for speed, and cross-encoder reranking of top-K results significantly improves NDCG.
[COMPAT]
- Python: sentence-transformers>=3.3.0 (Python 3.9+)
- Dependencies: transformers>=4.40.0, torch>=2.0.0, huggingface-hub>=0.20.0
- Models: BAAI/bge-m3, intfloat/multilingual-e5-large-instruct, nomic-ai/nomic-embed-text-v1.5, BAAI/bge-large-en-v1.5
[REFS]
- https://www.sbert.net/
- https://huggingface.co/sentence-transformers
- https://huggingface.co/spaces/mteb/leaderboard
- https://www.sbert.net/docs/package_reference/cross_encoder.html
