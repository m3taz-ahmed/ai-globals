#!/usr/bin/env python3
"""Sandboxed Code Mode executor.

Executes an agent-authored Python snippet in a restricted namespace. The
only privileged capability injected is ``call_tool(server, tool, args)``,
which routes every invocation through :mod:`runtime.enforcement` (MCP
firewall + AgentGateway) before dispatch — code mode never bypasses
governance.

Sandbox layers:

1. **AST scan** — reuses ``_is_plugin_source_safe`` (denylisted imports,
   dangerous calls, dunder/``__builtins__`` bypasses).
2. **Restricted builtins** — exec globals get a whitelist-only builtins
   dict; ``open``/``eval``/``__import__`` etc. are absent.
3. **Governed tool bridge** — ``call_tool`` goes through
   ``enforce_tool_call``/``enforce_tool_result``.
4. **Wall-clock timeout** — execution runs on a worker thread and the
   result is abandoned past ``timeout_s`` (the orphaned thread retains no
   privileges beyond the injected bridge).

This is a *cooperative* sandbox (no OS-level isolation): it raises the
bar against accidental misuse and injection-driven tool abuse, not a
determined in-process escape.
"""

from __future__ import annotations

import io
import json
import threading
from collections.abc import Callable
from contextlib import redirect_stdout
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from runtime.plugin import _is_plugin_source_safe

_SAFE_BUILTINS: dict[str, Any] = {
    "abs": abs, "all": all, "any": any, "bool": bool, "dict": dict,
    "enumerate": enumerate, "filter": filter, "float": float,
    "format": format, "int": int, "isinstance": isinstance, "len": len,
    "list": list, "map": map, "max": max, "min": min, "print": print,
    "range": range, "repr": repr, "round": round, "set": set,
    "sorted": sorted, "str": str, "sum": sum, "tuple": tuple, "zip": zip,
    "Exception": Exception, "ValueError": ValueError, "KeyError": KeyError,
    "TypeError": TypeError, "IndexError": IndexError, "True": True,
    "False": False, "None": None,
}


@dataclass
class CodeModeToolCall:
    """Audit record of a tool call made from inside a sandboxed snippet."""

    server: str
    tool: str
    decision: str  # allow/deny/ask
    ok: bool
    detail: str = ""


@dataclass
class CodeModeResult:
    """Outcome of a sandboxed snippet execution."""

    ok: bool
    output: str = ""
    error: str = ""
    tool_calls: list[CodeModeToolCall] = field(default_factory=list)
    timed_out: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "output": self.output,
            "error": self.error,
            "timed_out": self.timed_out,
            "tool_calls": [
                {"server": t.server, "tool": t.tool, "decision": t.decision, "ok": t.ok, "detail": t.detail}
                for t in self.tool_calls
            ],
        }


ToolCaller = Callable[[str, str, dict[str, Any]], dict[str, Any]]


class CodeModeExecutor:
    """Execute sandboxed snippets that call MCP tools."""

    def __init__(
        self,
        os_root: Path,
        tool_caller: ToolCaller | None = None,
        timeout_s: float = 15.0,
    ) -> None:
        self.os_root = os_root
        self._tool_caller = tool_caller or self._default_caller
        self.timeout_s = timeout_s

    def _default_caller(self, server: str, tool: str, args: dict[str, Any]) -> dict[str, Any]:
        from runtime.mcp_client import McpClient

        return McpClient(server, self.os_root).call_tool(tool, args)

    def execute(self, source: str) -> CodeModeResult:
        safe, reason = _is_plugin_source_safe(source, "<codemode>")
        if not safe:
            return CodeModeResult(ok=False, error=f"sandbox scan: {reason}")

        calls: list[CodeModeToolCall] = []
        stdout = io.StringIO()
        holder: dict[str, Any] = {}

        def call_tool(server: str, tool: str, args: dict[str, Any] | None = None) -> Any:
            args = args or {}
            decision = self._enforce(server, tool, args)
            if decision is not None:
                verdict = decision.get("decision", "deny")
                calls.append(
                    CodeModeToolCall(server, tool, verdict, False, str(decision.get("error") or decision.get("reason") or "denied"))
                )
                raise PermissionError(f"Tool call blocked ({verdict}): {decision.get('reason', 'denied')}")
            result = self._tool_caller(server, tool, args)
            result_text = json.dumps(result, default=str)
            ok, checked_text = self._enforce_result(server, tool, result_text)
            if not ok:
                calls.append(CodeModeToolCall(server, tool, "deny", False, "response blocked"))
                raise PermissionError(f"Tool result blocked: {checked_text}")
            calls.append(CodeModeToolCall(server, tool, "allow", True))
            try:
                return json.loads(checked_text)
            except json.JSONDecodeError:
                return checked_text

        def _run() -> None:
            ns: dict[str, Any] = {
                "__builtins__": dict(_SAFE_BUILTINS),
                "call_tool": call_tool,
            }
            try:
                with redirect_stdout(stdout):
                    exec(compile(source, "<codemode>", "exec"), ns)
            except BaseException as exc:
                holder["error"] = exc

        worker = threading.Thread(target=_run, daemon=True)
        worker.start()
        worker.join(timeout=self.timeout_s)
        if worker.is_alive():
            return CodeModeResult(
                ok=False, output=stdout.getvalue(), error=f"timeout after {self.timeout_s}s",
                tool_calls=calls, timed_out=True,
            )
        if "error" in holder:
            exc = holder["error"]
            if isinstance(exc, PermissionError):
                return CodeModeResult(ok=False, output=stdout.getvalue(), error=str(exc), tool_calls=calls)
            return CodeModeResult(
                ok=False, output=stdout.getvalue(), error=f"{type(exc).__name__}: {exc}", tool_calls=calls,
            )
        return CodeModeResult(ok=True, output=stdout.getvalue(), tool_calls=calls)

    def _enforce(self, server: str, tool: str, args: dict[str, Any]) -> dict[str, Any] | None:
        try:
            from runtime.enforcement import enforce_tool_call_root

            return enforce_tool_call_root(self.os_root, server, tool, args)
        except Exception as exc:
            return {"decision": "deny", "reason": f"enforcement error: {exc}"}

    def _enforce_result(self, server: str, tool: str, result_text: str) -> tuple[bool, str]:
        try:
            from runtime.enforcement import enforce_tool_result_root

            return enforce_tool_result_root(self.os_root, server, tool, result_text)
        except Exception:
            return True, result_text
