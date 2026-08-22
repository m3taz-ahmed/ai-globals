[TECH] LlamaIndex
[OBJ] Framework for building RAG pipelines with data connectors, indices, query engines, response synthesis, and LlamaParse document processing.
[RULES]
1. [REQ] Install with `pip install llama-index` (v0.12+) which uses `llama-index-core` plus integration packages; avoid the legacy `llama_index` (underscore) pre-0.10 packages.
2. [REQ] Use `Settings` global configuration (`from llama_index.core import Settings`) to set `llm`, `embed_model`, `chunk_size`, and `chunk_overlap`; do not pass these per-call in simple pipelines.
3. [REQ] Load documents with `SimpleDirectoryReader` for local files or LlamaHub connectors (`llama-index-readers-*`) for external sources; always verify `Document.metadata` is populated for source tracking.
4. [REQ] Use `VectorStoreIndex.from_documents(documents)` for standard RAG; for large corpora, use `VectorStoreIndex` with an external store (e.g., `llama-index-vector-stores-postgres` or `weaviate`).
5. [REQ] Build query engines with `index.as_query_engine(similarity_top_k=5)`; use `as_chat_engine` for conversational retrieval with memory.
6. [REQ] Use `ResponseSynthesizer` with `response_mode="compact"` (default) for most cases; use `"tree_summarize"` for long-context summarization and `"refine"` for iterative answer refinement.
7. [REQ] Use `SentenceSplitter` (from `llama_index.core.node_parser`) for chunking; set `chunk_size` and `chunk_overlap` based on the embedding model's context window (e.g., 1024/200 for most models).
8. [REQ] Use LlamaParse (`llama-index-readers-llama-parse`) for parsing PDFs, DOCX, and complex documents into structured markdown; requires `LLAMA_CLOUD_API_KEY` environment variable.
9. [REQ] Use `QueryFusionRetriever` or `AutoMergingRetriever` for advanced retrieval strategies; evaluate retrieval quality with `llama-index.core.evaluation` (Faithfulness, Relevancy evaluators).
10. [REQ] Use `llama-index-agent` packages for agentic RAG; `FnRetrieverOpenAIAgent` or LangGraph-style workflows for multi-step retrieval and tool use.
11. [REQ] Enable observability with `llama-index-callback-langfuse` or `llama-index-callback-arize` by setting the appropriate callback handler in `Settings.callback_manager`.
12. [CMD] `pip install llama-index llama-index-core llama-index-llms-openai llama-index-embeddings-openai` to install core plus OpenAI integrations.
13. [CMD] `export LLAMA_CLOUD_API_KEY="llx-..."` to enable LlamaParse.
14. [PROHIBIT] Never use the pre-0.10 monolithic `llama_index` API (`GPTVectorStoreIndex`, `ServiceContext`) in new code; migrate to `Settings` and `VectorStoreIndex`.
15. [PROHIBIT] Never store API keys in `Settings.llm = OpenAI(api_key="...")`; use environment variables or a `.env` file with `python-dotenv`.
[COMPAT]
- Python: llama-index>=0.12.0, llama-index-core>=0.12.0 (Python 3.9+)
- TS: llamaindex>=0.10.0 (Node 18+)
[REFS]
- https://docs.llamaindex.ai/
- https://docs.llamaindex.ai/en/stable/module_guides/querying/
- https://docs.cloud.llamaindex.ai/llamaparse
- https://docs.llamaindex.ai/en/stable/module_guides/evaluating/
