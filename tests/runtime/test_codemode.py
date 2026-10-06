"""Tests for runtime/codemode — sandboxed code-mode execution over MCP tools."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from runtime.codemode import CodeModeExecutor


def _executor(tmp_path: Path, caller=None, timeout: float = 10.0) -> CodeModeExecutor:
    return CodeModeExecutor(tmp_path, tool_caller=caller, timeout_s=timeout)


def test_simple_snippet_runs(tmp_path: Path) -> None:
    r = _executor(tmp_path).execute("print('hello' + ' ' + 'world')")
    assert r.ok and "hello world" in r.output


def test_dangerous_import_blocked(tmp_path: Path) -> None:
    r = _executor(tmp_path).execute("import os\nprint(os.getcwd())")
    assert not r.ok and "os" in r.error


def test_eval_blocked(tmp_path: Path) -> None:
    r = _executor(tmp_path).execute("eval('1+1')")
    assert not r.ok


def test_open_blocked(tmp_path: Path) -> None:
    r = _executor(tmp_path).execute("open('/etc/passwd')")
    assert not r.ok


def test_dunder_blocked(tmp_path: Path) -> None:
    r = _executor(tmp_path).execute("x = ().__class__.__bases__")
    assert not r.ok


def test_tool_call_routes_through_enforcement(tmp_path: Path) -> None:
    seen: list[tuple[str, str]] = []

    def caller(server: str, tool: str, args: dict) -> dict:
        seen.append((server, tool))
        return {"ok": True, "data": 42}

    ex = CodeModeExecutor(tmp_path, tool_caller=caller)
    with patch("runtime.enforcement.enforce_tool_call_root", return_value=None) as m_call, \
         patch("runtime.enforcement.enforce_tool_result_root", return_value=(True, '{"ok": true, "data": 42}')):
        r = ex.execute("res = call_tool('srv', 'read_thing', {'action': 'read'})\nprint(res['data'])")
    assert m_call.called
    assert r.ok and "42" in r.output and seen == [("srv", "read_thing")]
    assert r.tool_calls[0].decision == "allow"


def test_denied_tool_call_raises(tmp_path: Path) -> None:
    def caller(server, tool, args):  # pragma: no cover - must not be reached
        raise AssertionError("caller should not run")

    ex = CodeModeExecutor(tmp_path, tool_caller=caller)
    with patch(
        "runtime.enforcement.enforce_tool_call_root",
        return_value={"ok": False, "decision": "deny", "reason": "destructive"},
    ):
        r = ex.execute("call_tool('srv', 'delete_all')")
    assert (not r.ok and "denied" in r.error.lower()) or "blocked" in r.error.lower()
    assert r.tool_calls[0].decision == "deny"


def test_timeout(tmp_path: Path) -> None:
    r = _executor(tmp_path, timeout=0.5).execute(
        "x = 0\nwhile True:\n    x += 1"
    )
    assert not r.ok and r.timed_out


def test_syntax_error_reported(tmp_path: Path) -> None:
    r = _executor(tmp_path).execute("def broken(:\n")
    assert not r.ok and "Syntax" in r.error


def test_result_to_dict(tmp_path: Path) -> None:
    r = _executor(tmp_path).execute("print('hi')")
    d = r.to_dict()
    assert d["ok"] is True and "hi" in d["output"]


def test_default_caller_delegates_to_mcp_client(tmp_path: Path) -> None:
    with (
        patch("runtime.enforcement.enforce_tool_call_root", return_value=None),
        patch("runtime.mcp_client.McpClient") as mc,
    ):
        mc.return_value.call_tool.return_value = {"v": 1}
        r = CodeModeExecutor(tmp_path).execute("print(call_tool('srv', 't', {}))")
    assert r.ok


def test_result_blocked_by_enforcement(tmp_path: Path) -> None:
    ex = CodeModeExecutor(tmp_path, tool_caller=lambda s, t, a: {"secret": "x"})
    with (
        patch("runtime.enforcement.enforce_tool_call_root", return_value=None),
        patch(
            "runtime.enforcement.enforce_tool_result_root",
            return_value=(False, "redacted"),
        ),
    ):
        r = ex.execute("call_tool('srv', 't', {})")
    assert not r.ok and r.tool_calls[0].decision == "deny"


def test_result_non_json_returns_text(tmp_path: Path) -> None:
    ex = CodeModeExecutor(tmp_path, tool_caller=lambda s, t, a: {"result": "plain"})
    with (
        patch("runtime.enforcement.enforce_tool_call_root", return_value=None),
        patch(
            "runtime.enforcement.enforce_tool_result_root",
            return_value=(True, "{bad json"),
        ),
    ):
        r = ex.execute("res = call_tool('srv', 't', {})\nprint(res)")
    assert r.ok and "{bad json" in r.output


def test_generic_exception_in_code(tmp_path: Path) -> None:
    r = _executor(tmp_path).execute("x = 1 / 0")
    assert not r.ok and "ZeroDivisionError" in r.error


def test_enforce_call_error_denies(tmp_path: Path) -> None:
    ex = CodeModeExecutor(tmp_path, tool_caller=lambda s, t, a: {})
    with patch(
        "runtime.enforcement.enforce_tool_call_root",
        side_effect=RuntimeError("enf boom"),
    ):
        r = ex.execute("call_tool('srv', 't', {})")
    assert not r.ok and "enf boom" in r.error


def test_enforce_result_error_fails_open(tmp_path: Path) -> None:
    ex = CodeModeExecutor(tmp_path, tool_caller=lambda s, t, a: {"v": 9})
    with (
        patch("runtime.enforcement.enforce_tool_call_root", return_value=None),
        patch(
            "runtime.enforcement.enforce_tool_result_root",
            side_effect=RuntimeError("res boom"),
        ),
    ):
        r = ex.execute("print(call_tool('srv', 't', {}))")
    assert r.ok and "9" in r.output
