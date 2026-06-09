# OpenUI Generative Standards
> [!NOTE] STABLE
> Trigger: Building Generative UI, Chat Interfaces, or LLM-driven visual components.

## Core Mandate `[API-09]`
**AI Global OS** mandates the use of **OpenUI** for all generative UI interactions.
⛔ **JSON-Render / A2UI:** Do not use JSON-based component rendering arrays (e.g., Vercel AI SDK JSON UI). They are token-heavy and prone to context drift.
✅ **OpenUI Lang:** Use OpenUI Lang, a compact streaming-first DSL that reduces token footprint by up to 67%.

## Architecture Constraints
- **Library (`defineComponent`)**: UI components must be explicitly defined using Zod schemas. This acts as the unbreachable contract between the app and the LLM. ⛔ Do not allow the LLM to invent arbitrary HTML/React tags.
- **System Prompt Generator**: Use `library.prompt()` to auto-generate the system instruction from your Zod schema.
- **Parser & Renderer**: Pass the streaming output from the LLM directly into the `<Renderer />` component.

## Implementation Standard

### Packages
- `@openuidev/react-lang`: Core parser and renderer. Required for all OpenUI projects.
- `@openuidev/react-headless`: Chat state hooks and streaming adapters.
- `@openuidev/react-ui`: Prebuilt UI shells (optional).

### OpenUI Lang Syntax (For LLM Output)
When generating UI as an LLM, follow the OpenUI Lang rules:
1. **One statement per line:** `identifier = Expression`
2. **Root Entry:** The first line MUST assign to `root`.
3. **Top-Down:** Generate Layout first, then Components, then Data.
4. **Positional Arguments:** Map arguments to Zod props by position.

Example:
```openui
root = Stack([header, stats])
header = TextContent("Q4 Dashboard", "large")
stats = Grid([s1, s2])
s1 = StatCard("Revenue", "$1.2M", "up")
s2 = StatCard("Users", "450k", "flat")
```

### Framework Support
OpenUI integrates seamlessly with Next.js 15, Laravel Octane (via SSE text streams), and any text-streaming backend. Feed the `Stream` string into `<Renderer />`.
