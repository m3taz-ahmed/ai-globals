"""Code Mode: sandboxed code execution that calls MCP tools directly.

Instead of emitting tool-call JSON round-trips, the agent writes a small
Python snippet that invokes tools via ``call_tool(server, tool, args)`` —
cutting orchestration tokens substantially. Every tool call still routes
through the unified enforcement path (firewall + gateway), and the
snippet itself is AST-scanned and exec'd under a restricted builtins set.
"""

from __future__ import annotations

from runtime.codemode.executor import CodeModeExecutor, CodeModeResult, CodeModeToolCall

__all__ = ["CodeModeExecutor", "CodeModeResult", "CodeModeToolCall"]
