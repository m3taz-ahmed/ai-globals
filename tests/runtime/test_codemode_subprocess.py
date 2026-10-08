"""Tests for the subprocess-isolated codemode executor (C1/P0.2 fix).

Covers the child protocol module in-process (stream injection) and the
parent-side edge paths: spawn failure, child crash/EOF, protocol violation,
timeout kill, and plumbing helpers.
"""

from __future__ import annotations

import io
import json
import queue
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from runtime.codemode import _child
from runtime.codemode.executor import CodeModeExecutor


def _fake_child(tmp_path: Path, body: str) -> Path:
    script = tmp_path / "fake_child.py"
    script.write_text(body, encoding="utf-8")
    return script


def _with_child(tmp_path: Path, body: str, caller=None, timeout: float = 10.0) -> tuple[CodeModeExecutor, Path]:
    fake = _fake_child(tmp_path, body)
    ex = CodeModeExecutor(tmp_path, tool_caller=caller, timeout_s=timeout)
    return ex, fake


# ---------------------------------------------------------------------------
# _child protocol module (in-process via injected streams)
# ---------------------------------------------------------------------------


class TestChildProtocol:
    def test_send_writes_json_line(self) -> None:
        out = io.StringIO()
        _child._send(out, {"type": "x", "n": 1})
        assert json.loads(out.getvalue()) == {"type": "x", "n": 1}

    def test_pipe_stdout_forwards_writes(self) -> None:
        out = io.StringIO()
        tee = _child._PipeStdout(out)
        assert tee.write("hello") == 5
        assert json.loads(out.getvalue()) == {"type": "out", "data": "hello"}

    def test_pipe_stdout_empty_write_sends_nothing(self) -> None:
        out = io.StringIO()
        assert _child._PipeStdout(out).write("") == 0
        assert out.getvalue() == ""

    def test_call_tool_roundtrip(self) -> None:
        inp = io.StringIO(json.dumps({"ok": True, "result": 7}) + "\n")
        out = io.StringIO()
        call_tool = _child.make_call_tool(inp, out)
        assert call_tool("srv", "read", {"a": 1}) == 7
        sent = json.loads(out.getvalue().splitlines()[0])
        assert sent["type"] == "tool_call" and sent["server"] == "srv" and sent["args"] == {"a": 1}

    def test_call_tool_denied_raises(self) -> None:
        inp = io.StringIO(json.dumps({"ok": False, "error": "denied by policy"}) + "\n")
        out = io.StringIO()
        call_tool = _child.make_call_tool(inp, out)
        with pytest.raises(PermissionError, match="denied by policy"):
            call_tool("srv", "rm")

    def test_run_source_ok_streams_output(self) -> None:
        out = io.StringIO()
        done = _child.run_source("print('hi')", io.StringIO(), out)
        assert done == {"type": "done", "ok": True}
        streamed = "".join(json.loads(line)["data"] for line in out.getvalue().splitlines())
        assert streamed == "hi\n"

    def test_run_source_error_reports_exc_type(self) -> None:
        done = _child.run_source("x = 1 / 0", io.StringIO(), io.StringIO())
        assert done["ok"] is False and done["exc_type"] == "ZeroDivisionError"

    def test_main_executes_request(self) -> None:
        inp = io.StringIO(json.dumps({"source": "print(1 + 1)"}) + "\n")
        out = io.StringIO()
        assert _child.main(inp, out) == 0
        done = json.loads(out.getvalue().splitlines()[-1])
        assert done == {"type": "done", "ok": True}

    def test_main_bad_request_reports_child_error(self) -> None:
        out = io.StringIO()
        assert _child.main(io.StringIO("not json\n"), out) == 0
        done = json.loads(out.getvalue().splitlines()[-1])
        assert done["ok"] is False and done["exc_type"] == "ChildError"

    def test_main_detached_stdin_returns_error(self) -> None:
        with patch("sys.stdin", None), patch("sys.stdout", None):
            assert _child.main() == 1

    def test_main_detached_stdout_returns_error(self) -> None:
        with patch("sys.stdout", None):
            assert _child.main(io.StringIO('{"source": "pass"}\n')) == 1


# ---------------------------------------------------------------------------
# Parent executor edge paths
# ---------------------------------------------------------------------------


class TestExecutorEdgePaths:
    def test_spawn_failure(self, tmp_path: Path) -> None:
        ex = CodeModeExecutor(tmp_path)
        with patch("runtime.codemode.executor.subprocess.Popen", side_effect=OSError("no exec")):
            r = ex.execute("print(1)")
        assert not r.ok and "spawn failed" in r.error

    def test_request_write_failure(self, tmp_path: Path) -> None:
        ex = CodeModeExecutor(tmp_path)
        with patch.object(CodeModeExecutor, "_write_msg", return_value=False):
            r = ex.execute("print(1)")
        assert not r.ok and "request failed" in r.error

    def test_child_crash_reports_stderr(self, tmp_path: Path) -> None:
        ex, fake = _with_child(
            tmp_path,
            "import sys\nsys.stdin.readline()\nsys.stderr.write('boom reason\\n')\nsys.exit(3)\n",
        )
        with patch("runtime.codemode.executor._CHILD_SCRIPT", fake):
            r = ex.execute("print(1)")
        assert not r.ok and "without result" in r.error and "boom reason" in r.error

    def test_protocol_violation(self, tmp_path: Path) -> None:
        ex, fake = _with_child(tmp_path, "import sys\nsys.stdin.readline()\nprint('not json')\n")
        with patch("runtime.codemode.executor._CHILD_SCRIPT", fake):
            r = ex.execute("print(1)")
        assert not r.ok and "protocol violation" in r.error

    def test_timeout_kills_process(self, tmp_path: Path) -> None:
        r = CodeModeExecutor(tmp_path, timeout_s=0.4).execute("x = 0\nwhile True:\n    x += 1")
        assert not r.ok and r.timed_out

    def test_zero_timeout_expires_before_first_read(self, tmp_path: Path) -> None:
        # Line 141: the pre-read deadline check. timeout_s=0 makes `remaining`
        # <= 0 on the first pump iteration — deterministic, unlike the
        # between-iterations race this branch also covers.
        r = CodeModeExecutor(tmp_path, timeout_s=0).execute("print(1)")
        assert not r.ok and r.timed_out

    def test_tool_call_non_dict_args_coerced(self, tmp_path: Path) -> None:
        body = (
            "import json, sys\n"
            "sys.stdin.readline()\n"
            "sys.stdout.write(json.dumps({'type': 'mystery'}) + '\\n'); sys.stdout.flush()\n"
            "sys.stdout.write(json.dumps({'type': 'tool_call', 'id': 1, 'server': 's', "
            "'tool': 't', 'args': [1, 2]}) + '\\n'); sys.stdout.flush()\n"
            "sys.stdin.readline()\n"
            "sys.stdout.write(json.dumps({'type': 'done', 'ok': True}) + '\\n'); sys.stdout.flush()\n"
        )
        ex, fake = _with_child(tmp_path, body, caller=lambda s, t, a: {"v": 1})
        with (
            patch("runtime.codemode.executor._CHILD_SCRIPT", fake),
            patch("runtime.enforcement.enforce_tool_call_root", return_value=None),
            patch("runtime.enforcement.enforce_tool_result_root", return_value=(True, "{}")),
        ):
            r = ex.execute("call_tool('s', 't')")
        assert r.ok

    def test_done_error_without_exc_type(self, tmp_path: Path) -> None:
        body = (
            "import json, sys\nsys.stdin.readline()\n"
            "sys.stdout.write(json.dumps({'type': 'done', 'ok': False, 'error': 'plain fail'}) + '\\n')\n"
        )
        ex, fake = _with_child(tmp_path, body)
        with patch("runtime.codemode.executor._CHILD_SCRIPT", fake):
            r = ex.execute("print(1)")
        assert not r.ok and r.error == "plain fail"

    def test_done_error_empty_detail_uses_exc_type(self, tmp_path: Path) -> None:
        body = (
            "import json, sys\nsys.stdin.readline()\n"
            "sys.stdout.write(json.dumps({'type': 'done', 'ok': False, 'error': '', "
            "'exc_type': 'WeirdError'}) + '\\n')\n"
        )
        ex, fake = _with_child(tmp_path, body)
        with patch("runtime.codemode.executor._CHILD_SCRIPT", fake):
            r = ex.execute("print(1)")
        assert not r.ok and r.error == "WeirdError"


# ---------------------------------------------------------------------------
# Plumbing helpers
# ---------------------------------------------------------------------------


class _FakeProc:
    def __init__(self, poll_code=None, wait_raises: bool = False) -> None:
        self._poll = poll_code
        self._wait_raises = wait_raises
        self.killed = False

    def poll(self):
        return self._poll

    def kill(self):
        self.killed = True

    def wait(self, timeout=None):
        if self._wait_raises:
            raise subprocess.TimeoutExpired("cmd", 1)
        return 0


class _BadStream:
    def __iter__(self):
        raise OSError("stream gone")


class TestPlumbingHelpers:
    def test_write_msg_to_dead_process_returns_false(self, tmp_path: Path) -> None:
        proc = subprocess.Popen(
            [sys.executable, "-c", "pass"],
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            text=True,
        )
        proc.wait(timeout=10)
        assert CodeModeExecutor._write_msg(proc, {"a": 1}) is False

    def test_read_lines_none_stream_sends_eof(self) -> None:
        q: queue.Queue = queue.Queue()
        CodeModeExecutor._read_lines(None, q)
        assert q.get_nowait() is None

    def test_read_lines_oserror_sends_eof(self) -> None:
        q: queue.Queue = queue.Queue()
        CodeModeExecutor._read_lines(_BadStream(), q)
        assert q.get_nowait() is None

    def test_read_lines_normal_lines_then_eof(self) -> None:
        q: queue.Queue = queue.Queue()
        CodeModeExecutor._read_lines(io.StringIO("a\nb\n"), q)
        assert q.get_nowait() == "a\n" and q.get_nowait() == "b\n" and q.get_nowait() is None

    def test_drain_none_and_bad_streams(self) -> None:
        sink: list[str] = []
        CodeModeExecutor._drain(None, sink)
        CodeModeExecutor._drain(_BadStream(), sink)
        assert sink == []

    def test_drain_collects_lines(self) -> None:
        sink: list[str] = []
        CodeModeExecutor._drain(io.StringIO("e1\ne2\n"), sink)
        assert sink == ["e1\n", "e2\n"]

    def test_reap_kills_on_timeout(self) -> None:
        p = _FakeProc(wait_raises=True)
        CodeModeExecutor._reap(p)
        assert p.killed

    def test_reap_normal_exit(self) -> None:
        p = _FakeProc()
        CodeModeExecutor._reap(p)
        assert not p.killed

    def test_terminate_kills_running(self) -> None:
        p = _FakeProc()
        CodeModeExecutor._terminate(p)
        assert p.killed

    def test_terminate_swallows_wait_timeout(self) -> None:
        p = _FakeProc(wait_raises=True)
        CodeModeExecutor._terminate(p)
        assert p.killed

    def test_terminate_done_process(self) -> None:
        p = _FakeProc(poll_code=0)
        CodeModeExecutor._terminate(p)
        assert not p.killed
