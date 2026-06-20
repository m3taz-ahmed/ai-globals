[TECH] openui-generative
[OBJ] OpenUI Generative Standards.
[RULES]
1. [REQ] Mandate `[API-09]`: Use OpenUI Lang. ⛔ DO NOT use JSON-based component rendering arrays (too heavy).
2. [REQ] Architecture: Define components via Zod schemas (`defineComponent`). Parse directly into `<Renderer />`.
3. [REQ] Syntax: `identifier = Expression`. Root assignment first. Top-Down (Layout -> Comps -> Data). Positional arguments map to Zod props.
4. [REQ] Packages: `@openuidev/react-lang`, `@openuidev/react-headless`.
