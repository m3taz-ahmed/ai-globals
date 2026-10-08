#!/usr/bin/env python3
"""Codemode sandbox child process (C1 / P0.2).

Runs inside a dedicated ``subprocess.Popen`` spawned by
:class:`runtime.codemode.executor.CodeModeExecutor`. Because execution lives
in its own process, the parent can ``kill()`` it on timeout — guaranteeing
termination, which the previous daemon-thread design could not.

Protocol (one JSON object per line):

- Parent -> child (stdin): ``{"source": "<snippet>"}`` once, then a
  ``{"ok": true, "result": ...}`` / ``{"ok": false, "error": "..."}`` reply
  for every ``tool_call`` request the child emits.
- Child -> parent (stdout): ``{"type": "out", "data": str}`` for snippet
  prints, ``{"type": "tool_call", "id": n, "server": ..., "tool": ...,
  "args": {...}}`` for tool requests, and exactly one terminal
  ``{"type": "done", "ok": bool, ...}`` message.

This module is deliberately self-contained (no ``runtime.*`` imports) so the
child interpreter starts fast and cannot accidentally pull in privileged
helpers. All functions take injected streams so tests can exercise the full
protocol in-process.
"""

from __future__ import annotations

import io
import itertools
import json
import sys
from collections.abc import Callable
from contextlib import redirect_stdout
from typing import Any, TextIO, cast

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


def _send(out: TextIO, msg: dict[str, Any]) -> None:
    """Write one protocol message as a JSON line."""
    out.write(json.dumps(msg, default=str) + "\n")
    out.flush()


class _PipeStdout(io.TextIOBase):
    """stdout replacement that forwards snippet prints as ``out`` messages."""

    def __init__(self, out: TextIO) -> None:
        self._out = out

    def write(self, s: str) -> int:
        if s:
            _send(self._out, {"type": "out", "data": s})
        return len(s)


def make_call_tool(inp: TextIO, out: TextIO) -> Callable[..., Any]:
    """Build the ``call_tool`` bridge that round-trips through the parent."""
    counter = itertools.count(1)

    def call_tool(server: str, tool: str, args: dict[str, Any] | None = None) -> Any:
        _send(out, {
            "type": "tool_call", "id": next(counter),
            "server": server, "tool": tool, "args": args or {},
        })
        resp = json.loads(inp.readline())
        if not resp.get("ok"):
            raise PermissionError(resp.get("error", "denied"))
        return resp.get("result")

    return call_tool


def run_source(source: str, inp: TextIO, out: TextIO) -> dict[str, Any]:
    """Execute *source* in the restricted namespace; return the done message."""
    ns: dict[str, Any] = {
        "__builtins__": dict(_SAFE_BUILTINS),
        "call_tool": make_call_tool(inp, out),
    }
    try:
        # cast: _PipeStdout is a TextIOBase but type checkers won't narrow it
        # to IO[str] for redirect_stdout's parameter — duck-typing is correct
        # here (redirect only needs write()).
        with redirect_stdout(cast(TextIO, _PipeStdout(out))):
            exec(compile(source, "<codemode>", "exec"), ns)
    except BaseException as exc:
        return {
            "type": "done", "ok": False,
            "error": str(exc), "exc_type": type(exc).__name__,
        }
    return {"type": "done", "ok": True}


def main(inp: TextIO | None = None, out: TextIO | None = None) -> int:
    """Child entry point: read the exec request, run it, emit the done message."""
    inp = inp if inp is not None else sys.stdin
    out = out if out is not None else sys.stdout
    if inp is None or out is None:
        # Detached streams: the JSON-line protocol cannot run without both.
        return 1
    try:
        request = json.loads(inp.readline())
        result = run_source(str(request["source"]), inp, out)
    except BaseException as exc:
        result = {
            "type": "done", "ok": False,
            "error": f"child error: {exc}", "exc_type": "ChildError",
        }
    _send(out, result)
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess only
    sys.exit(main())
