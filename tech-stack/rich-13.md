[TECH] rich-13
[OBJ] Rich 13.x terminal formatting standards for aiZee CLI output.
[RULES]
1. [REQ] `from rich.console import Console`. `Console()` per command (not global).
2. [REQ] `rich.print()` for ad-hoc. `console.print()` for structured output.
3. [REQ] `rich.table.Table` for tabular CLI output (status, list commands).
4. [REQ] `rich.markdown.Markdown` for rendering `.md` help text.
5. [REQ] `rich.progress.Progress` for long-running operations. Context manager.
6. [REQ] `rich.panel.Panel` for boxed warnings/errors. `rich.syntax.Syntax` for code blocks.
7. [REQ] Detect `NO_COLOR` env var / non-TTY: fall back to plain text.
8. [PROHIBIT] `rich.__version__` (attribute missing in some builds). Use `importlib.metadata.version("rich")`.
9. [PROHIBIT] Rich markup in log records (breaks structured logging). Use plain text in logs.
[COMPAT]
- v13.9: current installed. Stable API.
[REFS]
- rich.readthedocs.io
