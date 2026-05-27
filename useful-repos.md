# Useful Repositories & Tools

This file tracks useful open-source repositories and tools that can be leveraged when building new features. Before starting a new feature, review this list to see if any existing tool can simplify the implementation.

## Integrations & APIs
- **[NangoHQ/nango](https://github.com/NangoHQ/nango)**: An open-source platform for B2B integrations.
  - **Use Case**: When building features that require integrating with third-party APIs (Google, Slack, Salesforce, etc.), handling OAuth flows, managing token refreshes, or acting as an API proxy.
  - **Key Benefits**: Provides out-of-the-box OAuth handling for 800+ APIs, a secure proxy for authenticated requests without managing headers manually, and the ability to run sync logic as serverless functions (`TypeScript`). Ideal for AI Agents needing access to user tools.

## AI Methodologies & Agent Frameworks
- **[obra/superpowers](https://github.com/obra/superpowers)**: A software development methodology and plugin system for AI coding agents.
  - **Use Case**: When organizing how AI agents execute tasks (planning, test-driven development, autonomous subagent execution).
  - **Key Benefits**: Forces AI agents to pause and plan specs instead of rushing to code, enforces Red/Green TDD (Test-Driven Development), and utilizes subagent-driven development for executing isolated engineering tasks autonomously without deviating from the plan.

## UI/UX & Design
- **[VoltAgent/awesome-design-md](https://github.com/VoltAgent/awesome-design-md)**: A curated list of semantic design system documents and UI contexts for AI coding agents.
  - **Use Case**: When building new frontend features, generating UI components, or aligning AI output with modern design standards.
  - **Key Benefits**: Provides structured markdown-based design guidelines that help AI agents understand and adhere to the project's visual identity, typography, and layout rules.
