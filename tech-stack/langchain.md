[TECH] LangChain
[OBJ] Framework for building LLM applications using LCEL chains, agents, RAG pipelines, memory, callbacks, LangSmith tracing, and LangGraph stateful orchestration.
[RULES]
1. [REQ] Use LangChain >=0.3 which is built on LangGraph and LangSmith; install with `pip install langchain langchain-core langchain-openai` — avoid the monolithic `langchain` pre-0.1 packages.
2. [REQ] Use the LangChain Expression Language (LCEL) with the pipe operator (`prompt | llm | parser`) for composable chains; always use `Runnable` interfaces rather than legacy `LLMChain` classes.
3. [REQ] Initialize model integrations from `langchain-openai`, `langchain-anthropic`, etc.; never import models from the base `langchain` package (deprecated in 0.3).
4. [REQ] Use `ChatPromptTemplate` for prompt construction; pass variables via `.invoke({"var": value})` or `.batch([...])` for parallel execution.
5. [REQ] For RAG, use `langchain_community` or `langchain_postgres` vector stores with `OpenAIEmbeddings` or `HuggingFaceEmbeddings`; retrieve with `as_retriever(search_kwargs={"k": 5})`.
6. [REQ] Use `StrOutputParser` for plain text and `PydanticOutputParser` (or `with_structured_output(schema)`) for structured data; never parse model output with raw string splitting.
7. [REQ] Enable LangSmith tracing by setting `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY`, and `LANGSMITH_PROJECT` environment variables; trace all chains for debugging and evaluation.
8. [REQ] Use LangGraph (`langgraph`) for stateful, multi-step agent workflows with `StateGraph`, `add_node`, `add_edge`, and `compile()`; prefer LangGraph over legacy `AgentExecutor`.
9. [REQ] Use `BaseCallbackHandler` or the `with_config(callbacks=[...])` method for custom logging, monitoring, and metric collection; do not insert print statements into chain logic.
10. [REQ] For memory in conversational chains, use `RunnableWithMessageHistory` with a `BaseChatMessageHistory` backend (e.g., `RedisChatMessageHistory` for production); avoid in-memory `ConversationBufferMemory` in multi-instance deployments.
11. [REQ] Use `tool` decorator from `langchain_core.tools` to define tools; pass `tools=[...]` to `create_react_agent` from `langgraph.prebuilt`.
12. [CMD] `pip install langchain langchain-core langchain-openai langgraph langsmith` to install the full stack.
13. [CMD] `export LANGSMITH_TRACING=true LANGSMITH_API_KEY=lsv2_... LANGSMITH_PROJECT=my-project` to enable tracing.
14. [PROHIBIT] Never use deprecated `LLMChain`, `ConversationChain`, `AgentExecutor`, or `load_qa_chain` in new code; migrate to LCEL and LangGraph equivalents.
15. [PROHIBIT] Never hardcode API keys in `OpenAI(api_key="...")` calls; always pass `api_key=os.environ["OPENAI_API_KEY"]` or rely on auto-env detection.
[COMPAT]
- Python: langchain>=0.3.0, langchain-core>=0.3.0, langgraph>=0.2.0 (Python 3.9+)
- JS/TS: @langchain/core>=0.3.0, @langchain/langgraph>=0.2.0 (Node 18+)
[REFS]
- https://python.langchain.com/docs/concepts/lcel
- https://langchain-ai.github.io/langgraph/
- https://docs.smith.langchain.com/
- https://python.langchain.com/docs/tutorials/rag
