#!/usr/bin/env python3
"""Sandboxed Code Mode executor.

Executes an agent-authored Python snippet in a restricted namespace inside a
dedicated subprocess (:mod:`runtime.codemode._child`). The only privileged
capability injected is ``call_tool(server, tool, args)``, which round-trips
to the parent over a JSON-lines pipe and routes every invocation through
:mod:`runtime.enforcement` (MCP firewall + AgentGateway) before dispatch —
code mode never bypasses governance.

Sandbox layers:

1. **AST scan** — reuses ``_is_plugin_source_safe`` (denylisted imports,
   dangerous calls, dunder/``__builtins__`` bypasses).
2. **Restricted builtins** — the child execs with a whitelist-only builtins
   dict; ``open``/``eval``/``__import__`` etc. are absent.
3. **Governed tool bridge** — ``call_tool`` goes through
   ``enforce_tool_call``/``enforce_tool_result`` in the *parent* process.
4. **Process isolation + timeout** — execution runs in a spawned child
   process; on timeout the parent ``kill()``s it, guaranteeing termination.
   The previous thread-based sandbox could only *abandon* a timed-out
   worker while it kept executing with ``call_tool`` in scope (C1).

This is a *cooperative* sandbox (no OS-level sandboxing/pledge): it raises
the bar against accidental misuse and injection-driven tool abuse, and it
now guarantees a timed-out snippet cannot keep issuing tool calls.
"""

from __future__ import annotations

import contextlib
import json
import logging
import queue
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TextIO

from runtime.plugin import _is_plugin_source_safe

_logger = logging.getLogger(__name__)

_CHILD_SCRIPT = Path(__file__).resolve().with_name("_child.py")
_STDERR_TAIL = 500


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
    """Execute sandboxed snippets that call MCP tools, in a child process."""

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

    # -- Public entry point ------------------------------------------------

    def execute(self, source: str) -> CodeModeResult:
        safe, reason = _is_plugin_source_safe(source, "<codemode>")
        if not safe:
            return CodeModeResult(ok=False, error=f"sandbox scan: {reason}")
        calls: list[CodeModeToolCall] = []
        try:
            proc = subprocess.Popen(
                [sys.executable, "-u", str(_CHILD_SCRIPT)],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", errors="replace",
            )
        except OSError as exc:
            return CodeModeResult(ok=False, error=f"sandbox spawn failed: {exc}")
        try:
            return self._pump(proc, source, calls)
        finally:
            self._terminate(proc)

    # -- Subprocess protocol pump ------------------------------------------

    def _pump(self, proc: subprocess.Popen[str], source: str, calls: list[CodeModeToolCall]) -> CodeModeResult:
        out_parts: list[str] = []
        err_parts: list[str] = []
        lines: queue.Queue[str | None] = queue.Queue()
        threading.Thread(target=self._read_lines, args=(proc.stdout, lines), daemon=True).start()
        threading.Thread(target=self._drain, args=(proc.stderr, err_parts), daemon=True).start()
        if not self._write_msg(proc, {"source": source}):
            return self._crash_result(proc, calls, out_parts, err_parts, "sandbox request failed")
        deadline = time.monotonic() + self.timeout_s
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return self._timeout_result(proc, calls, out_parts)
            try:
                line = lines.get(timeout=remaining)
            except queue.Empty:
                return self._timeout_result(proc, calls, out_parts)
            if line is None:
                return self._crash_result(proc, calls, out_parts, err_parts, "sandbox exited without result")
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                return self._crash_result(proc, calls, out_parts, err_parts, "sandbox protocol violation")
            msg_type = msg.get("type")
            if msg_type == "out":
                out_parts.append(str(msg.get("data", "")))
            elif msg_type == "tool_call":
                self._answer_tool_call(proc, msg, calls)
            elif msg_type == "done":
                return self._done_result(proc, msg, calls, out_parts)

    def _answer_tool_call(self, proc: subprocess.Popen[str], msg: dict[str, Any], calls: list[CodeModeToolCall]) -> None:
        args = msg.get("args")
        resp = self._dispatch_tool_call(
            str(msg.get("server", "")), str(msg.get("tool", "")),
            args if isinstance(args, dict) else {}, calls,
        )
        self._write_msg(proc, resp)

    def _dispatch_tool_call(self, server: str, tool: str, args: dict[str, Any], calls: list[CodeModeToolCall]) -> dict[str, Any]:
        decision = self._enforce(server, tool, args)
        if decision is not None:
            verdict = decision.get("decision", "deny")
            calls.append(
                CodeModeToolCall(server, tool, verdict, False, str(decision.get("error") or decision.get("reason") or "denied"))
            )
            return {"ok": False, "error": f"Tool call blocked ({verdict}): {decision.get('reason', 'denied')}"}
        result = self._tool_caller(server, tool, args)
        result_text = json.dumps(result, default=str)
        ok, checked_text = self._enforce_result(server, tool, result_text)
        if not ok:
            calls.append(CodeModeToolCall(server, tool, "deny", False, "response blocked"))
            return {"ok": False, "error": f"Tool result blocked: {checked_text}"}
        calls.append(CodeModeToolCall(server, tool, "allow", True))
        try:
            return {"ok": True, "result": json.loads(checked_text)}
        except json.JSONDecodeError:
            return {"ok": True, "result": checked_text}

    # -- Result builders ----------------------------------------------------

    def _done_result(self, proc: subprocess.Popen[str], msg: dict[str, Any], calls: list[CodeModeToolCall], out_parts: list[str]) -> CodeModeResult:
        output = "".join(out_parts)
        self._reap(proc)
        if msg.get("ok"):
            return CodeModeResult(ok=True, output=output, tool_calls=calls)
        exc_type = str(msg.get("exc_type") or "")
        detail = str(msg.get("error") or "")
        if exc_type in ("PermissionError", "ChildError", ""):
            error = detail
        else:
            error = f"{exc_type}: {detail}" if detail else exc_type
        return CodeModeResult(ok=False, output=output, error=error, tool_calls=calls)

    def _timeout_result(self, proc: subprocess.Popen[str], calls: list[CodeModeToolCall], out_parts: list[str]) -> CodeModeResult:
        return CodeModeResult(
            ok=False, output="".join(out_parts), error=f"timeout after {self.timeout_s}s",
            tool_calls=calls, timed_out=True,
        )

    def _crash_result(self, proc: subprocess.Popen[str], calls: list[CodeModeToolCall], out_parts: list[str], err_parts: list[str], reason: str) -> CodeModeResult:
        code = proc.poll()
        detail = f"{reason} (exit code {code})"
        tail = "".join(err_parts).strip()[-_STDERR_TAIL:]
        if tail:
            detail += f": {tail}"
        return CodeModeResult(ok=False, output="".join(out_parts), error=detail, tool_calls=calls)

    # -- Process plumbing ---------------------------------------------------

    @staticmethod
    def _write_msg(proc: subprocess.Popen[str], msg: dict[str, Any]) -> bool:
        try:
            assert proc.stdin is not None
            proc.stdin.write(json.dumps(msg, default=str) + "\n")
            proc.stdin.flush()
        except (OSError, ValueError):
            return False
        return True

    @staticmethod
    def _read_lines(stream: TextIO | None, sink: queue.Queue[str | None]) -> None:
        try:
            if stream is not None:
                for line in stream:
                    sink.put(line)
        except (OSError, ValueError):
            pass
        finally:
            sink.put(None)

    @staticmethod
    def _drain(stream: TextIO | None, sink: list[str]) -> None:
        try:
            if stream is not None:
                for line in stream:
                    sink.append(line)
        except (OSError, ValueError):
            pass

    @staticmethod
    def _reap(proc: subprocess.Popen[str]) -> None:
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    @staticmethod
    def _terminate(proc: subprocess.Popen[str]) -> None:
        if proc.poll() is None:
            proc.kill()
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.wait(timeout=5)

    # -- Governance bridge --------------------------------------------------

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
        except Exception as exc:
            _logger.warning("codemode result enforcement error (degraded): %s", exc)
            return True, result_text
