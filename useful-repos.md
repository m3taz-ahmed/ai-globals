# Useful Repositories & Tools

This file tracks useful open-source repositories and tools that can be leveraged when building new features. Before starting a new feature, review this list to see if any existing tool can simplify the implementation.

## Integrations & APIs
- **[NangoHQ/nango](https://github.com/NangoHQ/nango)**: An open-source platform for B2B integrations.
  - **Use Case**: When building features that require integrating with third-party APIs (Google, Slack, Salesforce, etc.), handling OAuth flows, managing token refreshes, or acting as an API proxy.
  - **Key Benefits**: Provides out-of-the-box OAuth handling for 800+ APIs, a secure proxy for authenticated requests without managing headers manually, and the ability to run sync logic as serverless functions (`TypeScript`). Ideal for AI Agents needing access to user tools.

- **[alistaitsacle/free-llm-api-keys](https://github.com/alistaitsacle/free-llm-api-keys)**: A repository containing free, auto-updated, multi-model compatible LLM API keys.
  - **Use Case**: When testing or developing AI-driven features (completions, streaming, embeddings, image generation) locally, in staging, or within CI/CD pipelines without purchasing/exposing paid production keys.
  - **Key Benefits**: Free multi-model rotation-backed keys (supporting GPT-5.5, Claude, Gemini, DeepSeek, Kimi) compatible with the standard OpenAI API client. Fully automated rotation script handles key updates and cleanup daily.


## AI Methodologies & Agent Frameworks
- **[obra/superpowers](https://github.com/obra/superpowers)**: A software development methodology and plugin system for AI coding agents.
  - **Use Case**: When organizing how AI agents execute tasks (planning, test-driven development, autonomous subagent execution).
  - **Key Benefits**: Forces AI agents to pause and plan specs instead of rushing to code, enforces Red/Green TDD (Test-Driven Development), and utilizes subagent-driven development for executing isolated engineering tasks autonomously without deviating from the plan.

## UI/UX & Design
- **[VoltAgent/awesome-design-md](https://github.com/VoltAgent/awesome-design-md)**: A curated list of semantic design system documents and UI contexts for AI coding agents.
  - **Use Case**: When building new frontend features, generating UI components, or aligning AI output with modern design standards.
  - **Key Benefits**: Provides structured markdown-based design guidelines that help AI agents understand and adhere to the project's visual identity, typography, and layout rules.

## Ingestion & Document Parsing
- **[adithya-s-k/omniparse](https://github.com/adithya-s-k/omniparse)**: A local ingestion and parsing platform that converts unstructured data (documents, images, audio, video, web) into structured Markdown for GenAI (LLM) applications.
  - **Use Case**: When building RAG systems (e.g. using Qdrant), analyzing design wireframes/screenshots for UI generation, transcribing media specs, or crawling dynamic web pages.
  - **Key Benefits**: Completely local and private deployment (via Docker), parses PDF, Word, PowerPoint, images, web, and audio/video into clean LLM-friendly Markdown. Exposes FastAPI endpoints and a Gradio UI.

## Awesome Lists (Curated Resources)
- **[ziadoz/awesome-php](https://github.com/ziadoz/awesome-php)**: A curated list of amazingly awesome PHP libraries, resources, and shiny things.
  - **Use Case**: When looking for the best standard library or tool in PHP for a specific task (e.g. PDF generation, caching, ORM).
- **[simskij/awesome-software-architecture](https://github.com/simskij/awesome-software-architecture)**: A curated list of awesome articles and resources to learn and practice software architecture.
  - **Use Case**: When designing a new system or refactoring an existing one.
- **[vinta/awesome-python](https://github.com/vinta/awesome-python)**: A curated list of awesome Python frameworks, libraries, software and resources.
  - **Use Case**: When working on python/AI scripts and needing a specific tool.
- **[enaqx/awesome-react](https://github.com/enaqx/awesome-react)**: A collection of awesome things regarding React ecosystem.
  - **Use Case**: When working on React frontend projects.
